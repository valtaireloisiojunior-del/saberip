const express = require('express');
const fs = require('fs');
const path = require('path');
const app = express();

app.use(express.json({ limit: '5mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(express.static(__dirname)); // servir arquivos estáticos

// Rota para criar a ferramenta
app.post('/criar-ferramenta', (req, res) => {
    const { titulo, descricao, icone, categoria, html } = req.body;

    if(!titulo || !html || !categoria) return res.status(400).json({ error: 'Campos obrigatórios faltando' });

    // Criar slug do arquivo
    const slug = titulo.toLowerCase().replace(/[^a-z0-9]+/g,'-') + '.html';
    const pasta = path.join(__dirname, categoria);

    // Certificar que a pasta existe
    if(!fs.existsSync(pasta)) fs.mkdirSync(pasta);

    // Criar HTML da ferramenta
    const htmlCompleto = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${titulo} | SEUIP.COM.BR</title>
<meta name="description" content="${descricao}">
<style>
body {font-family:Arial,sans-serif; background:#0d0d0d; color:#f0f0f0; padding:20px;}
header {text-align:center; margin-bottom:30px;}
header h1 {color:#00ff99;}
.tool-container {max-width:900px; margin:0 auto; padding:20px; background:#111; border-radius:15px; border:2px solid #222;}
</style>
</head>
<body>
<header>
<h1>${titulo}</h1>
<p>${descricao}</p>
<a href="../index.html" style="color:#00ff99;">⬅ Voltar para Home</a>
</header>
<div class="tool-container">
${html}
</div>
</body>
</html>`;

    const caminhoArquivo = path.join(pasta, slug);

    // Salvar HTML
    fs.writeFileSync(caminhoArquivo, htmlCompleto, 'utf8');

    // Atualizar JSON de ferramentas
    const jsonPath = path.join(__dirname, 'ferramentas.json');
    let ferramentas = [];
    if(fs.existsSync(jsonPath)) {
        ferramentas = JSON.parse(fs.readFileSync(jsonPath));
    }

    ferramentas.push({
        titulo,
        descricao,
        icone,
        categoria,
        link: `${categoria}/${slug}`
    });

    fs.writeFileSync(jsonPath, JSON.stringify(ferramentas, null, 2), 'utf8');

    res.json({ message: 'Ferramenta criada com sucesso!', arquivo: `${categoria}/${slug}` });
});

// Iniciar servidor
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Servidor rodando na porta ${PORT}`));
