
# hn-sentiment

ChatOps comando de barra para análise de sentimento de notícias do Hacker News.

## Instructions

Crie um comando de barra ChatOps chamado /curitiba. Quando um usuário postar um comentário em uma issue do GitHub que comece com "/curitiba <url>", onde <url> é a URL de uma notícia do Hacker News (por exemplo, https://news.ycombinator.com/item?id=12345), faça o seguinte:
0) Tudo tem que ser escrito em português do Brasil.
1) Extraia o ID da notícia do Hacker News da URL.
2) Busque até 50 comentários principais dessa notícia na API do Hacker News.
3) Realize uma análise de sentimento no texto do comentário, classificando cada comentário como Positivo, Negativo ou Neutro.
4) Gere um resumo que mostre: o sentimento geral (com a porcentagem de distribuição), os 3 comentários mais positivos (com trecho) e os 3 comentários mais negativos (com trecho).

5) Responda ao comentário original da issue com a análise formatada em Markdown.

Se nenhuma URL for fornecida ou se a URL não for uma notícia válida do Hacker News, responda com uma mensagem de erro útil e um poema sarcástico sobre a importância de fornecer uma URL válida, para animar o dia do usuário.
