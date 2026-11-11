# Como eu trabalho com IA neste projeto

> Rascunho em revisão. A versão em inglês vem depois que este texto for aprovado.

**Em poucas linhas:** o Garimpei é um comparador de preços que estou construindo
para mim e, se der certo, para outras pessoas. Comecei escrevendo o código à mão,
com a arquitetura desenhada por mim. Hoje desenvolvo com o Claude Code: eu decido
o produto e a arquitetura, a IA propõe, implementa e verifica, e nada entra na
`main` sem passar por testes automáticos, pelo CI e pela minha aprovação. Este
documento mostra o que é meu, o que veio da IA, como eu confiro o resultado e
onde a IA errou.

Não documento cada prompt. Isso seria inviável e diz pouco. O que interessa é o
que eu decidi, o que eu corrigi e como eu verifico.

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

**Os limites, com honestidade:**

- Ainda não há usuários reais nem deploy de produção; tudo roda localmente.
  A ida para a AWS é um próximo passo, também como estudo.
- Recuperação de senha e e-mail de boas-vindas não existem neste repositório.
- Não há planos de lançamento comercial por enquanto: a meta é ter algo que
  funcione para mim e esteja pronto para outras pessoas.

## 2. Como cheguei aqui

| Quando | O que aconteceu |
|---|---|
| dez/2025 | Primeiros commits, escritos à mão, sem IA nenhuma (nem Copilot). O primeiro commit (7/dez) já tinha repositório com interface, casos de uso e validador |
| 13/dez/2025 | Reestruturação para ficar mais alinhada à Arquitetura Limpa, que eu estava estudando |
| fev/2026 | Testes unitários, de integração e ponta a ponta, e o CI no GitHub Actions. Ideia e decisão minhas |
| até abr/2026 | Usei o GitHub Copilot; em abril fiz um experimento com o Qwen |
| abr/2026 | Juntei o back-end e o front-end, que eram repositórios separados, neste monorepo. Parte do histórico antigo ficou para trás |
| out/2026 em diante | Passei a usar o Claude Code. O primeiro commit assinado por ele é de 24/out/2026 |
| nov/2026 | Mudança de rumo: de "monitor de oportunidades por palavra-chave" para comparador de preços, com novo e usado lado a lado |

## 3. Quem faz o quê

**Eu:**

- decido o produto: o que construir, em que ordem e o que fica de fora;
- desenho e cuido da arquitetura (com a ajuda da IA para polir, mas a
  responsabilidade é minha);
- defino a estratégia de testes e as barreiras de proteção (seção 7);
- respondo às rodadas de perguntas dos planos e aprovo cada um;
- testo o resultado como usuário e aprovo cada merge.

**O Claude Code:**

- propõe planos com perguntas, para eu decidir;
- implementa em fatias pequenas, um PR por fatia;
- roda os testes, sobe o ambiente local, tira prints de celular e desktop;
- só pede o merge com o CI verde e mostra a evidência.

### A arquitetura

O projeto segue a Arquitetura Limpa, que não é um molde com nome (como a
hexagonal), e sim um conjunto de princípios: o domínio no centro, as
dependências apontando para dentro, os detalhes (banco, framework, e-mail) nas
bordas. Alguns desses princípios estão no código desde antes da IA:

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

Em 2026 o código passou a ser organizado por módulos de domínio (`catalog`,
`alerts`), a chamada "screaming architecture", em passos pequenos, sem parar o
resto do trabalho.

## 4. O ciclo de trabalho

Exemplo real: a Fase 5, que moveu a área do usuário para o site novo.

1. **Plano com perguntas.** O Claude levanta o que existe e me faz uma rodada
   de perguntas. Por exemplo: login por e-mail, por usuário ou pelos dois? O
   que "Meus alertas" precisa mostrar? Eu respondo, e as respostas viram
   decisões registradas em [`docs/plan/phase-5-user-area.md`](plan/phase-5-user-area.md).
2. **Fatias pequenas, um PR por fatia:** API da conta (#90), sessão (#91),
   alertas (#92), conta (#93), admin só para administradores (#94), fechamento
   (#95).
3. **Verificação antes de pedir o merge:** testes unitários, typecheck, build,
   testes ponta a ponta no navegador contra o ambiente local e prints.
4. **Meu OK.** O merge só acontece depois que eu aprovo, e cada PR precisa de
   uma aprovação nova.
5. **O plano é atualizado** a cada fatia, com as decisões novas.

Quando o rumo muda no meio do caminho, o plano muda junto. A própria Fase 5
nasceu assim: testei o botão "Me avise" da Fase 4 e caí numa interface antiga,
que não combinava com o resto. Parei e decidimos mover a área do usuário.

## 5. Duas decisões explicadas

### A área do usuário no site novo (Next.js), não no app antigo (Vite)

- **Contexto:** o app antigo foi feito para alertas por palavra-chave, com outra
  aparência (azul, Material UI). O site novo, com a identidade do Garimpei, tinha
  só as páginas públicas.
- **Alternativa:** redesenhar o app antigo com a identidade nova.
- **Por que não:** seriam duas bases de front-end para manter, com o usuário
  pulando entre elas. Concentrar tudo o que o usuário faz no site novo deixa
  uma única experiência.
- **Limitação que ficou:** o painel de administração continua no app antigo,
  com outra aparência. **Próximo passo:** levar o admin também para o Next, com
  a mesma identidade, e aposentar o Vite.

### Não raspar a Amazon (nem sites parecidos)

- **Contexto:** a Amazon seria a referência de preço de livro novo.
- **Alternativa:** um coletor lento, imitando uma pessoa. Tecnicamente
  possível.
- **Por que não:** o risco é contratual. Raspar a loja enquanto participo do
  programa de afiliados pode custar a conta de afiliado, e os termos de uso
  proíbem. O mesmo vale para sites com regras parecidas.
- **Limitação que ficou:** sem o preço novo da Amazon na comparação, a página
  mostra um link de busca de afiliado no lugar.

## 6. Como eu verifico

Decidi cedo que o projeto teria muitos testes. Hoje:

| Parte | Testes | Ferramenta |
|---|---|---|
| Back-end (API) | 876 | pytest |
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
  sistema de verdade.
- **Ainda não testado:** carga (muitos usuários ao mesmo tempo), entrega real de
  e-mail fora da caixa falsa e qualquer coisa de produção.

## 7. Onde a IA errou e o que pegou

A IA erra. O que importa é ter barreiras que peguem o erro antes da `main`.
Alguns casos reais:

| O erro | O que pegou | O que mudou |
|---|---|---|
| Ao editar com scripts, trocou finais de linha (CRLF/LF) e inflou os diffs | Revisão do diff | Regra escrita: manter os finais de linha de cada arquivo |
| Alertas de livro eram barrados pelo limite do plano grátis | Teste ponta a ponta com a conta do plano grátis | Frequência fixa de um dia para alertas de livro (#87) |
| Testes supunham "401" onde a API devolve "400" (login errado) e "403" (sem token) | Os próprios testes falharam | Ajustados ao comportamento real e documentado (#90) |
| O site ia mandar para o login em qualquer "403", inclusive "limite do plano" | Leitura do controller antes de implementar | Só o "401" pede novo login; o "403" vira mensagem (#92) |
| O hook do ruff (formatador) deixava uma linha em branco sobrando | Teste do hook antes de publicar | Ordem corrigida (#96) |
| Testes E2E com rótulos chutados e o menu recolhido | O print da falha | Seletores pelos rótulos reais (#98) |
| `pre-commit run --all-files` alterou arquivos antigos, inclusive uma migration já aplicada | `git status` antes de commitar | Alterações desfeitas; ajuste na configuração (#97) |
| Enquadrou o produto como "para leitores" | Eu | Regra registrada: comparador geral, livros são só a primeira categoria |

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

| Camada | O que pega | O que não pega |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) (lido pelo Claude via `CLAUDE.md`) | Desvios das regras da casa: arquitetura, uma fatia por PR, como verificar, armadilhas conhecidas | Nada à força: é instrução, não trava |
| Permissões ([`.claude/settings.json`](../.claude/settings.json)) | Push, merge, `docker compose down` e migrations sempre pedem minha confirmação; editar o `.env` é negado | Comandos que não estão na lista |
| Hooks ([`.claude/hooks/`](../.claude/hooks/)) | Edição de `.env` e de migrations que já estão na `main` (bloqueia); Python fora do padrão (corrige na hora) | Erros de lógica |
| pre-commit | Formatação, JSON/YAML inválidos, conflitos esquecidos, nos meus commits e nos da IA | Comportamento |
| CI | Lint, tipos, testes e build de cada parte, a cada PR | Fluxos completos no navegador (ainda não roda o E2E) |
| Testes E2E | Fluxos reais de usuário, do clique ao e-mail | Só rodam localmente, quando alguém os roda |
| Meu OK | Se faz sentido para o produto; o que nenhum teste mede | Depende de eu revisar com atenção |

## 9. O que eu domino e o que ainda estou estudando

Seguindo um conselho que li: se ainda não entendo uma parte do código gerado,
volto a ela antes de apresentá-la como algo que domino.

- **Explico bem:** o front-end, as requisições, os endpoints e controllers, como
  o FastAPI funciona, e a arquitetura (casos de uso, repositórios, portas e
  adaptadores, injeção de dependência).
- **Explico o conceito, mas preciso relembrar a ferramenta:** filas e broker
  (Celery com Redis). Isso deve mudar na ida para a AWS.
- **Preciso estudar:** a sessão por cookie no Next.js e a regra do veredito de
  preço (compara o menor preço de hoje com os percentis 25 e 75 dos últimos
  90 dias), que foi ideia da IA e que eu aprovei.

## 10. Próximos passos

Cada um com um critério de "funcionou":

| Próximo passo | Funcionou quando… |
|---|---|
| Rodar os testes E2E no CI | Um PR que quebra o fluxo do "Me avise" fica vermelho sozinho |
| Levar o admin para o Next.js, com a identidade do Garimpei | O app antigo (Vite) pode ser apagado e os testes do admin passam no site |
| Recuperação de senha e e-mail de boas-vindas | Um usuário recebe o e-mail, troca a senha e entra com a nova |
| Ir para a AWS | O site roda fora da minha máquina, dentro do limite de custo que defini |
| Estudar a sessão por cookie e a regra do veredito | Consigo explicar cada uma em um minuto, sem consultar o código |
