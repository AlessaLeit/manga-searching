# Documento de Requisitos - Manga Searching

## 1. Introdução
O presente documento descreve os requisitos para o desenvolvimento de uma plataforma web voltada à pesquisa e organização de informações sobre mangás, com foco na centralização de dados provenientes de múltiplas fontes e na facilitação da comparação de ofertas e disponibilidade.

## 2. Problema Identificado
A aquisição de mangás físicos costuma envolver uma busca dispersa em diferentes plataformas, o que torna o processo demorado, fragmentado e pouco eficiente. A ausência de uma solução unificada dificulta a localização de títulos, preços, condições de venda e fontes confiáveis.

## 3. Justificativa
A criação de uma plataforma automatizada é justificável pela necessidade de reduzir o esforço manual na busca por mangás, oferecendo uma experiência mais ágil e organizada. A solução permite que o usuário encontre informações relevantes de forma centralizada, compare opções de compra e tome decisões mais informadas.

## 4. Objetivo Geral
Desenvolver uma plataforma web que permita a busca, organização e apresentação de informações sobre mangás a partir de diferentes fontes, com o objetivo de centralizar a pesquisa e facilitar o acesso a dados relevantes para o usuário.

## 5. Objetivos Específicos
- Coletar dados de sites de venda e outras fontes disponíveis;
- Exibir informações referentes ao mangá, incluindo estado de conservação, valor, média de preço, avaliação do vendedor e link para leitura online, quando houver;
- Organizar os resultados de forma pesquisável e comparável;
- Facilitar a identificação das melhores opções de compra com base em critérios definidos pelo usuário.

## 6. Descrição do Processo Atual
Atualmente, o processo de pesquisa por mangás é realizado manualmente, geralmente por meio de buscas em diferentes sites e aplicativos de venda. Esse procedimento exige a análise individual de cada resultado, além da comparação entre preços, condições de produtos e reputação de vendedores, o que torna a experiência menos prática e mais suscetível a erros.

## 7. Requisitos Funcionais
O sistema deverá:
- permitir a busca de mangás por nome;
- realizar a coleta automática de informações de anúncios e preços;
- exibir os resultados de forma organizada para o usuário;
- aplicar filtros e ordenação com base em critérios como preço e disponibilidade;
- direcionar o usuário para o anúncio correspondente, quando necessário.

## 8. Requisitos Não Funcionais
- A interface deve ser intuitiva e de fácil utilização;
- O sistema deve processar as informações de forma ágil;
- As informações apresentadas devem ser atualizadas e consistentes;
- A solução deve ser compatível com ambientes web modernos.

## 9. Tecnologias Pretendidas
- Python
- Flask
- Selenium/Playwright
- JavaScript
- React

## 10. Funcionalidades Previstas
- Pesquisa de mangás;
- Classificação por categoria, como online, usado ou novo;
- Apresentação de informações detalhadas sobre cada item;
- Redirecionamento para o anúncio correspondente.
