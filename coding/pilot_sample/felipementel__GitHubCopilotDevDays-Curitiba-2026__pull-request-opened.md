
# pull-request-opened

Analise de pull request aberto: "${{ github.event.pull_request.title }}". Adicione um comentário com um resumo dos próximos passos, como sugestões de revisão, testes a serem realizados ou informações adicionais necessárias para avançar com a revisão do pull request.

## Instructions

Analise do pull request seguindo os seguintes critérios:
- Verifique se o título e a descrição estão claros e informativos. Caso esteja vazio, solicite ao autor que forneça mais detalhes.
- Identifique se há arquivos de código modificados e, se possível, forneça feedback inicial sobre a estrutura do código, padrões de codificação ou possíveis áreas de melhoria.
- Se o pull request estiver relacionado a um problema específico, verifique se ele está vinculado corretamente e se a descrição aborda a solução proposta para o problema.
- Se o pull request incluir testes, verifique se eles estão bem escritos e cobrem os casos de uso relevantes. Se não houver testes, sugira que sejam adicionados para garantir a qualidade do código.
- Forneça orientações sobre o processo de revisão, como quem deve revisar o código, quais áreas específicas devem ser focadas ou se há alguma etapa adicional necessária antes da revisão, como a execução de testes locais ou a verificação de dependências.
- Coloque uma tag adequada para indicar o status do pull request, utilizando as tags disponíveis no repositório.
- Se houver alguma informação faltando ou se o pull request não atender aos critérios mínimos, forneça um feedback construtivo e solicite as correções necessárias para avançar com a revisão.
- Se estiver tudo correto, atribua para o usuario @felipementel e adicione um comentário de aprovação, indicando que o pull request está pronto para revisão.
