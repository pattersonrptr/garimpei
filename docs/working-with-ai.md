# Como eu trabalho com IA neste projeto

> 🇬🇧 [Read in English](working-with-ai.en.md) (tradução; o original é este).

O Garimpei é um comparador de preços que estou construindo
para mim e, se der certo, para outras pessoas. Comecei escrevendo o código à mão,
com a arquitetura desenhada por mim. Hoje desenvolvo com o Claude Code: eu decido
o produto e a arquitetura, a IA propõe, implementa e verifica, e nada entra na
`main` sem passar por testes automáticos, pelo CI e pela minha validação.

**Por que este documento existe:** quero registrar como eu trabalho com IA, para
aprender com isso e levar o que funciona para outros projetos. Ele também mostra,
com exemplos reais, o que eu sei e como eu trabalho: o que é meu, o que veio da
IA, como eu confiro o resultado e onde a IA errou.

---

## 1. O problema e os limites

**O problema:** quando quero comprar algo, especialmente um livro, preciso abrir
várias lojas, comparar novo e usado e adivinhar se o preço de hoje é bom ou se
vale esperar. O Garimpei junta as ofertas novas e usadas lado a lado, guarda o
histórico, diz se o preço está "bom", "normal" ou "caro agora" e avisa por
e-mail quando o preço chega no valor que eu quero.

**Por que livros primeiro:** o ISBN torna quase trivial saber que dois anúncios
de lojas diferentes são o mesmo produto, e essa é a parte mais difícil de um
comparador. Um casamento errado é pior do que nenhum. Os livros também têm
metadados gratuitos (BrasilAPI) e um mercado de usados forte (Estante Virtual,
OLX, Enjoei). O modelo de dados já nasceu genérico (produto, identificador,
oferta) para outras categorias entrarem depois.

**Também é um projeto de estudo:** escolhi FastAPI e Arquitetura Limpa para
fixar esses dois conhecimentos, e a ida para a nuvem vai ser o meu caminho para
aprender AWS.

**Os limites, com honestidade:**

- Ainda não há usuários reais nem deploy de produção; tudo roda localmente.
- Recuperação de senha e e-mail de boas-vindas não existem neste repositório.
- A meta, por enquanto, é ter algo que funcione para mim e esteja pronto para
  outras pessoas, sem plano de lançamento comercial. Por isso, desde o começo,
  a arquitetura comporta vários usuários (contas, planos, alertas por usuário):
  quando chegarem mais pessoas, a base já está pronta para elas.

## 2. Como cheguei aqui

É um projeto paralelo, feito em cerca de 5 horas por semana, ao lado do
trabalho e de outros projetos pessoais. O ritmo da tabela reflete isso.

| Quando | O que aconteceu |
|---|---|
| dez/2025 | Primeiros commits, escritos à mão, sem IA nenhuma (nem Copilot). O primeiro commit (7/dez) já tinha repositório com interface, casos de uso e validador |
| 13/dez/2025 | Reestruturação para ficar mais alinhada à Arquitetura Limpa, que eu estava estudando |
| fev/2026 | Testes unitários, de integração e ponta a ponta, e o CI no GitHub Actions. Ideia e decisão minhas |
| até abr/2026 | Usei o GitHub Copilot; em abril fiz um experimento com o Qwen |
| abr/2026 | Juntei o back-end e o front-end, que eram repositórios separados, neste monorepo |
| out/2026 | Passei a usar o Claude Code (primeiro commit assinado por ele: 24/out) |
| nov/2026 | Mudança de rumo: de "monitor de oportunidades por palavra-chave" para comparador de preços. Planejada em 9/nov e entregue em fatias pequenas, uma por PR, ao longo do mês |

## 3. Quem faz o quê

**Eu:**

- decido o produto: o que construir, em que ordem e o que fica de fora;
- desenho e cuido da arquitetura;
- defino a estratégia de testes e as barreiras de proteção (seção 8);
- respondo às rodadas de perguntas dos planos e aprovo cada um;
- testo o resultado como usuário e digo o que precisa mudar.

**O Claude Code:**

- propõe planos com perguntas, para eu decidir;
- sugere caminhos e aponta o que acha que está errado, inclusive no que eu
  pedi;
- implementa em fatias pequenas, um PR por fatia;
- roda os testes, sobe o ambiente local, tira prints de celular e desktop;
- faz o merge sozinho quando o CI fica verde, com a evidência no PR.

Na prática funciona como uma programação em par: eu tenho a palavra final, mas
as decisões saem da conversa.

### A arquitetura

O projeto é a minha implementação da Arquitetura Limpa: o domínio no centro, as
dependências apontando para dentro, os detalhes (banco, framework, e-mail) nas
bordas. Mantenho anotações próprias sobre Arquitetura Limpa e outros temas de
engenharia de software, e a IA lê essas anotações para entender como eu penso a
arquitetura antes de propor mudanças. As regras que saem delas estão no
[plano principal](plan/README.md#4-architecture-rules).

Alguns desses princípios estão no código desde antes da IA:

| Ideia | Onde está | Desde |
|---|---|---|
| **Repository** com interface (o caso de uso depende da interface, não do banco) | `UserRepositoryInterface` e a implementação SQLAlchemy | 1º commit, 7/dez/2025 |
| **Caso de uso**: uma classe por ação (responsabilidade única, o "S" do SOLID) | `CreateUserUseCase`, `GetUserByIdUseCase`, … | 1º commit |
| **Validador** separado das regras de negócio | `UserValidator` | 1º commit |
| **Presenter**: o formato da resposta (JSON:API) fora do controller | `UserPresenter` e os outros | 13/dez/2025 |
| **Injeção de dependência** | `Depends(...)` do FastAPI montando repositórios e casos de uso | desde o início |
| **Strategy**: trocar a implementação sem mudar quem usa (o "O" do SOLID) | `EmailServiceInterface` com SMTP ou SendGrid; `IsbnMatcher` para casar ofertas por categoria | 2026 |
| **Portas e adaptadores**: o módulo que precisa de algo define a interface (porta); outro módulo fornece o adaptador | `alerts` define `ProductSnapshotReader` e `BookFinder`; o adaptador é feito sobre o `catalog` | nov/2026 |

**Portas** são interfaces: usadas com injeção de dependência, deixam os módulos
isolados, porque qualquer um que implemente a interface pode ser plugado. É o
"D" do SOLID (inversão de dependência). **Adaptadores** (o padrão Adapter)
protegem o domínio dos detalhes. Tudo isso facilita os testes: o caso de uso é
testado com um adaptador falso, sem banco.

O código tem alguns padrões táticos do Domain-Driven Design (entidades,
repositórios, módulos com nomes do domínio), mas eles vieram da Arquitetura
Limpa, que compartilha essas ideias, e não de um estudo de DDD. Ainda não li
sobre DDD; está na minha lista.

Desde nov/2026 o back-end está sendo reorganizado por domínio (`catalog`,
`alerts`), a chamada *screaming architecture*: as pastas dizem o que o sistema
faz, não qual framework ele usa. A mudança vai em passos pequenos, um módulo por
PR, sem parar o resto do trabalho.

**Ferramentas:** FastAPI, SQLAlchemy e Alembic com PostgreSQL no back-end;
Celery com Redis nos coletores; Next.js no site público; React com Vite no
painel de administração; tudo rodando em Docker Compose.

## 4. O ciclo de trabalho

Exemplo real: a Fase 5, que moveu a área do usuário para o site novo.

1. **Plano com perguntas.** O Claude levanta o que existe e me faz uma rodada
   de perguntas. Por exemplo: login por e-mail, por usuário ou pelos dois? O
   que "Meus alertas" precisa mostrar? Eu respondo, e as respostas viram
   decisões registradas em [`docs/plan/phase-5-user-area.md`](plan/phase-5-user-area.md).
2. **Fatias pequenas, um PR por fatia:** API da conta (#90), sessão (#91),
   alertas (#92), conta (#93), admin só para administradores (#94), fechamento
   (#95).
3. **Verificação antes do merge:** testes unitários, typecheck, build,
   testes ponta a ponta no navegador contra o ambiente local e prints.
4. **Merge com o CI verde.** Desde 11/nov/2026 a IA faz o merge sozinha
   quando todos os checks do CI passam; se algo fica vermelho, ela corrige
   antes. Eu deixei de ser o gargalo dos PRs verdes: a proteção da `main` no
   GitHub recusa o merge sem os checks, até para mim. Minha validação passou a
   ser usar o sistema e apontar o que precisa mudar, e as decisões de produto
   e arquitetura continuam comigo.
5. **O plano é atualizado** a cada fatia, com as decisões novas.

Quando o rumo muda no meio do caminho, o plano muda junto. A própria Fase 5
nasceu assim: testei o botão "Me avise" da Fase 4 e caí numa interface antiga,
que não combinava com o resto. Parei e decidimos mover a área do usuário.

## 5. Algumas decisões explicadas

### Um site em Next.js, e não só o app em React (Vite)

- **Contexto:** o projeto começou com um app em React (Vite) feito para alertas
  por palavra-chave. Ele roda no navegador do usuário: as páginas nascem
  vazias e o JavaScript as monta.
- **Por que mudar:** um comparador vive de páginas públicas (busca, página do
  livro) que o Google precisa ler e que precisam abrir rápido no celular. O
  Next.js entrega essas páginas já prontas pelo servidor (SSR), o que ajuda no
  SEO e na velocidade. Foi uma sugestão da IA no planejamento, e eu concordei.
- **Como:** sem migração de uma vez só. O site começou só com as páginas
  públicas (Fase 3); a área do usuário veio depois (Fase 5).
- **Limitação que ficou:** o painel de administração continua no app antigo,
  com outra aparência. **Próximo passo:** levar o admin para o Next, com a
  mesma identidade, e aposentar o Vite.

### Só coletar de quem permite

- **Regra:** não raspo lojas cujos termos proíbem a coleta, como a Amazon. A
  Amazon entra pelo programa de afiliados: hoje com um link de busca, e com
  preços pela API oficial quando a conta de afiliado cumprir os requisitos.
- **Por quê:** além dos termos de uso, raspar uma loja da qual sou afiliado
  pode custar a conta de afiliado.
- **Limitação que ficou:** sem o preço novo da Amazon na comparação, a página
  mostra o link de busca de afiliado no lugar.

### Coletar com educação

- **Regra:** os coletores usam requisições HTTP simples sempre que o preço está
  no HTML, e um navegador só quando a página depende de JavaScript. Respeitam o
  `robots.txt`, fazem pausas de 5 a 15 segundos e param a loja no dia ao
  primeiro bloqueio. Não burlam captcha nem usam proxies.
- **Alternativa recusada:** contornar bloqueios para coletar mais lojas.
- **Por quê:** evitar risco jurídico e bloqueio de IP. Prefiro menos lojas a
  coletar de forma abusiva.

### Sessão em cookie que o JavaScript não lê

- **Decisão:** no site, o token de login fica num cookie `httpOnly`, gravado só
  pelo servidor, e não no `localStorage`.
- **Por quê:** um script malicioso na página não consegue ler o token.
- **Custo:** a renovação do token passa pelo servidor do Next, o que deu mais
  trabalho do que guardar no navegador.

### Refatorar aos poucos, nunca de uma vez

- **Decisão:** a reorganização por domínio vai um módulo por PR, sem mudar o
  comportamento, e a mudança de front-end vai página por página.
- **Alternativa recusada:** reescrever tudo de uma vez.
- **Por quê:** cada passo pequeno é testável e reversível, e o projeto continua
  funcionando no meio do caminho.

## 6. Como eu verifico

Decidi cedo que o projeto teria muitos testes. Hoje:

| Parte | Testes | Ferramenta |
|---|---|---|
| Back-end (API) | 884 | pytest |
| Coletores | 313 | pytest |
| Site público | 75 | Vitest |
| Painel admin | 75 | Vitest |
| Ponta a ponta (navegador) | 32 | Playwright |

- **CI:** a cada PR, o GitHub Actions roda lint, checagem de tipos, testes e
  build de cada parte. O merge só acontece com tudo verde.
- **Testes ponta a ponta (E2E):** o Playwright abre um navegador e faz o que um
  usuário faria: abre um livro, clica em "Me avise", entra, cria o alerta,
  confere o cartão e o e-mail que chega no Mailpit (uma caixa de e-mail falsa
  local). **Ainda rodam só localmente**, antes de cada merge, e não no CI.
- **Manual:** prints de celular e desktop a cada mudança visual, e eu uso o
  sistema de verdade. Os prints e o vídeo do README saem de um script do
  Playwright ([`frontend/e2e/media/`](../frontend/e2e/media/tour.media.ts)),
  então dá para refazê-los quando as telas mudam.
- **Ainda não testado:** carga (muitos usuários ao mesmo tempo), entrega real de
  e-mail fora da caixa falsa e qualquer coisa de produção.

## 7. Onde a IA errou e quem pegou

A IA erra. O que importa é ter barreiras que peguem o erro antes da `main`.

### Erros pegos pelas barreiras automáticas

| O erro | O que pegou | O que mudou |
|---|---|---|
| Ao editar com scripts, trocou finais de linha (CRLF/LF) e inflou os diffs | Revisão do diff | Regra escrita: manter os finais de linha de cada arquivo |
| Alertas de livro eram barrados pelo limite do plano grátis | Teste ponta a ponta com a conta do plano grátis | Frequência fixa de um dia para alertas de livro (#87) |
| Testes supunham "401" onde a API devolve "400" (login errado) e "403" (sem token) | Os próprios testes falharam | Ajustados ao comportamento real e documentado (#90) |
| O site ia mandar para o login em qualquer "403", inclusive "limite do plano" | Leitura do controller antes de implementar | Só o "401" pede novo login; o "403" vira mensagem (#92) |
| O hook do ruff (formatador) deixava uma linha em branco sobrando | Teste do hook antes de publicar | Ordem corrigida (#96) |
| Testes E2E com rótulos chutados e o menu recolhido | O print da falha | Seletores pelos rótulos reais (#98) |
| `pre-commit run --all-files` alterou arquivos antigos, inclusive uma migration já aplicada | `git status` antes de commitar | Alterações desfeitas; ajuste na configuração (#97) |
| O hook que bloqueia `--no-verify` barrou o próprio commit que o criava, porque a mensagem citava a flag | O próprio hook, ao entrar em vigor | Ele passou a olhar só os argumentos de comandos git de verdade (#101) |
| O script de prints clicava no botão "Buscar" da barra do topo em vez do "Entrar" | O print de falha que o próprio script salva | Seletor restrito ao formulário de login (#102) |
| O vídeo de demonstração tinha 1,4 MB, acima do limite de arquivos do repositório | O pre-commit (`check-added-large-files`) | O script comprime o vídeo com ffmpeg (#110) |
| O exemplo do `docker-compose.override.yml` usa a tag `!override`, que não é YAML comum | O pre-commit (`check-yaml`) | O arquivo ficou fora dessa checagem; quem valida é o `docker compose config` (#105) |
| O script de mídia escolheu sozinho um livro sem capa e com o novo a R$ 750 | Olhando os prints antes de publicar | O livro dos prints passou a ser fixo, configurável (#110) |
| O e-mail de alerta ainda tinha a cara do app antigo (azul, "R$ 17.46", `estante_virtual`) | Olhando o print do e-mail para o README | E-mail com a identidade do Garimpei (#111) |

### Erros que eu peguei

| O erro | Como eu percebi | O que mudou |
|---|---|---|
| A IA enquadrou o produto como "para leitores" | Lendo os textos e o plano | Regra registrada: comparador geral, livros são só a primeira categoria |
| O "Me avise" levava para o app antigo, com outra cara e outra lógica | Usando o sistema como usuário | Virou a Fase 5: toda a área do usuário no site novo |
| O painel de admin ainda mostrava "Meus alertas" e "Planos", telas de usuário | Navegando pelo painel | As telas saíram do admin (#98) |

### Um caso em detalhe: o alerta que o plano grátis barrava

- **O problema:** o botão "Me avise" criava um alerta com a frequência padrão
  dos alertas antigos (a cada 60 minutos). O plano grátis não permite essa
  frequência, e a API respondia "limite do plano atingido". Os testes unitários
  passavam, porque usavam outra conta.
- **Como apareceu:** no teste ponta a ponta, com a conta de cliente do plano
  grátis, o alerta não era criado.
- **A investigação:** a frequência só faz sentido para buscas por palavra-chave.
  Os livros são coletados uma vez por dia e o alerta é checado quando chega uma
  oferta nova.
- **A correção:** alertas de livro usam frequência fixa de um dia, e o teste
  ponta a ponta passou a cobrir esse caminho.
- **A conferência:** o mesmo teste, de novo, com o e-mail chegando no Mailpit.

## 8. As camadas de proteção

Há uma diferença importante entre elas: o `AGENTS.md` é **instrução**. A IA
segue, mas nada a impede de desviar, e eu mesmo posso pedir para ela ignorar
uma regra. Permissões e hooks são **travas**: quem as aplica é o Claude Code,
não o modelo, então a IA não consegue pular. E tudo isso só vale para a IA: as
proteções no GitHub valem para qualquer pessoa.

| Camada | O que pega | O que não pega |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) (lido pelo Claude via `CLAUDE.md`) | Desvios das regras da casa: arquitetura, uma fatia por PR, como verificar, armadilhas conhecidas | Nada à força: é instrução, não trava |
| Permissões ([`.claude/settings.json`](../.claude/settings.json)) | `docker compose down` e migrations pedem minha confirmação; editar o `.env` e acessar a Amazon são negados. O push de um branch de trabalho e o merge de PR são livres, porque as travas abaixo já protegem a `main` | Comandos que não estão na lista (um `curl` para a Amazon, por exemplo) |
| Hooks ([`.claude/hooks/`](../.claude/hooks/)) | Bloqueiam: edição de `.env` e de migrations que já estão na `main`; commit ou push na `main`, force push, pular o pre-commit e merge forçado. Pedem minha confirmação antes de qualquer mudança nas próprias travas (`.claude/`). Corrigem Python fora do padrão | Erros de lógica |
| pre-commit | Qualidade de código: formatação, JSON/YAML inválidos, conflitos esquecidos, nos meus commits e nos da IA | Comportamento |
| Proteção da `main` no GitHub | Vale para qualquer pessoa, inclusive eu: só entra por PR com os quatro checks do CI verdes, sem force push e sem apagar a `main`. É ela que deixa a IA fazer o merge sozinha | O conteúdo do PR |
| CI (GitHub Actions) | Lint, tipos, testes e build de cada parte, a cada PR | Fluxos completos no navegador (ainda não roda o E2E) |
| Testes E2E | Fluxos reais de usuário, do clique ao e-mail | Só rodam localmente, quando alguém os roda |
| Skill [`e2e-local`](../.claude/skills/e2e-local/SKILL.md) | O teste ponta a ponta como receita: o que reconstruir, esperar os serviços, rodar o Playwright, tirar prints | Só roda quando é chamada |
| Subagente [`architecture-reviewer`](../.claude/agents/architecture-reviewer.md) | Violações das minhas regras de arquitetura num diff (regra da dependência, portas, entidades puras) | Bugs e estilo; é uma segunda opinião, não uma trava |
| Minha validação | Se faz sentido para o produto; o que nenhum teste mede | Depende de eu revisar com atenção |

### Automatizar o que se repete

Só transformo em skill, subagente ou hook o que eu já faço à mão várias vezes
(YAGNI): nada entra só para mostrar que sei configurar. Além de evitar erros,
isso economiza tokens. O resumo de início de sessão é um script que entrega,
em quatro linhas, o branch, os PRs abertos e o que falta do plano, em vez de a
IA levantar isso a cada sessão. A skill de teste ponta a ponta já traz os
passos e as armadilhas conhecidas. Quando a IA percebe uma tarefa repetida,
ela propõe a automação e o modelo adequado: um mais barato para passos
mecânicos, um mais forte para revisões.

## 9. O que eu domino e o que ainda estou estudando

Seguindo um conselho que li: se ainda não entendo uma parte do código gerado,
volto a ela antes de apresentá-la como algo que domino.

- **Explico bem:** o front-end, as requisições, os endpoints e controllers, como
  o FastAPI funciona, e a arquitetura (casos de uso, repositórios, portas e
  adaptadores, injeção de dependência).
- **Explico o conceito, mas preciso relembrar a ferramenta:** filas e broker
  (Celery com Redis).
- **Preciso estudar:** a sessão por cookie no Next.js e a regra do veredito de
  preço (compara o menor preço de hoje com os percentis 25 e 75 dos últimos
  90 dias), que foi ideia da IA e que eu aprovei. Também quero ler sobre
  Domain-Driven Design.

Este documento vai mudar junto com o projeto e com o que eu aprender. Quando
algo aqui ficar desatualizado, a IA propõe a alteração e eu reviso antes.

## 10. Próximos passos

Cada um com um critério de "funcionou". O plano completo está em
[`docs/plan/README.md`](plan/README.md).

| Próximo passo | Funcionou quando… |
|---|---|
| Rodar os testes E2E no CI | Um PR que quebra o fluxo do "Me avise" fica vermelho sozinho |
| Levar o admin para o Next.js, com a identidade do Garimpei | O app antigo (Vite) pode ser apagado e os testes do admin passam no site |
| Recuperação de senha e e-mail de boas-vindas | Um usuário recebe o e-mail, troca a senha e entra com a nova |
| Ir para a AWS | O site roda fora da minha máquina, dentro do limite de custo que defini |
| Estudar a sessão por cookie e a regra do veredito | Consigo explicar cada uma em um minuto, sem consultar o código |
