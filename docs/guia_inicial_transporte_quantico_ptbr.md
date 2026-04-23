# Guia Inicial em PT-BR: Entendendo o Lab de Transporte Quântico

Este guia é para você ler devagar, do zero, sem assumir que você já conhece
transporte quântico em redes, sistemas abertos ou a equação de Lindblad.

O objetivo aqui não é impressionar. É fazer você entender o que o laboratório
está simulando, o que cada termo quer dizer e como ler os gráficos.

## 1. O que estamos estudando, em português claro

A pergunta central do projeto é:

**como uma excitação quântica se move em um grafo pequeno quando existe tanto
evolução quântica coerente quanto efeitos dissipativos do ambiente?**

Aqui:

- um **grafo** é uma rede de pontos ligados entre si;
- a **excitação** é algo como “a energia/partícula está neste nó”;
- a palavra **coerente** quer dizer que a evolução segue a mecânica quântica de
  forma unitária, com interferência;
- a palavra **dissipativo** quer dizer que o ambiente atrapalha, mede, desfasa
  ou drena parte da dinâmica.

## 2. O que cada coisa do grafo significa

Nos nossos gráficos:

- cada **nó** é um site físico possível para a excitação;
- cada **aresta** é um acoplamento entre dois sites;
- o número dentro do nó é o índice do site: `0`, `1`, `2`, ...

Exemplo:

- numa `chain`, só vizinhos se ligam;
- num `ring`, a cadeia fecha em círculo;
- num `complete`, todo nó liga com todo nó.

Então a topologia do grafo diz **por quais caminhos a excitação pode circular**.

## 3. O que significa “a excitação está num nó”

Se o sistema tem `N` nós, usamos a base:

```math
|0\rangle, |1\rangle, |2\rangle, \dots, |N-1\rangle
```

Interpretando:

- `|2>` significa: “a excitação está localizada no nó 2”.

Se ela estiver puramente no nó 2 no tempo inicial, isso é a condição inicial do
experimento numérico.

## 4. O que é o Hamiltoniano aqui

O Hamiltoniano é a regra que diz como a parte quântica coerente evolui.

No nosso caso usamos um Hamiltoniano do tipo `tight-binding`:

```math
H = \sum_i \epsilon_i |i\rangle\langle i| + \sum_{i\neq j} J_{ij}|i\rangle\langle j|
```

Leitura física:

- `\epsilon_i`: energia local do nó `i`;
- `J_ij`: acoplamento entre os nós `i` e `j`.

Se `J_ij` é grande, a excitação consegue “saltar” com mais facilidade entre
esses nós.

## 5. O que é um sistema quântico aberto

Você já viu muita mecânica quântica em que o sistema fica isolado e evolui
unitariamente.

Aqui **não** estamos assumindo isolamento perfeito.

Estamos assumindo que o sistema conversa com um ambiente.

Isso significa que:

- coerências podem se perder;
- parte da população pode escapar;
- o sistema pode deixar de evoluir como um sistema fechado.

Por isso chamamos isso de **sistema quântico aberto**.

## 6. O que é matriz densidade e por que usamos isso

Em vez de descrever o sistema só por um vetor de estado, usamos uma
**matriz densidade** `rho`.

Por quê?

Porque ela serve tanto para:

- estados puros;
- estados mistos;
- evolução com dissipação.

Diagonal de `rho`:

- são as populações dos nós.

Fora da diagonal:

- são as coerências quânticas entre os nós.

Então:

- `rho_ii(t)` = população do nó `i`;
- `rho_ij(t)` com `i != j` = coerência entre os nós `i` e `j`.

## 7. O que é a equação de Lindblad

Essa é a primeira grande novidade conceitual.

A equação de Lindblad é uma forma padrão de modelar evolução quântica aberta de
forma efetiva:

```math
\frac{d\rho}{dt}
= -i[H,\rho] + \sum_k \left( L_k \rho L_k^\dagger - \frac12 \{L_k^\dagger L_k,\rho\} \right)
```

Leitura intuitiva:

- `-i[H,\rho]`: parte coerente, quântica, parecida com a evolução usual;
- os termos com `L_k`: canais dissipativos do ambiente.

Você pode pensar assim:

- o Hamiltoniano faz a excitação circular;
- os operadores de Lindblad dizem como o ambiente estraga, mede ou drena essa dinâmica.

## 8. O que é dephasing

O caso dissipativo mais importante aqui é a **dephasagem**.

Ela não destrói diretamente a população de cada nó.
Ela destrói principalmente a **coerência** entre os nós.

Na prática:

- a parte quântica “ondulatória” vai ficando menos importante;
- a interferência vai sendo reduzida;
- isso pode ajudar ou atrapalhar o transporte.

Esse é justamente um dos temas físicos centrais do projeto.

## 9. O que é o sink

Esse é o termo que mais estava te confundindo.

O `sink` é um **estado absorvente de sucesso**.

Ele não é um nó físico do grafo.

Ele representa:

**“a excitação chegou ao destino útil”**

Então:

- a população que entra no `sink` é contada como transporte bem-sucedido;
- a quantidade final no `sink` é a nossa medida principal de eficiência.

Em fórmula:

```math
\eta(T) = \rho_{ss}(T)
```

onde `s` é o sink.

Interpretação:

- `eta(T)` perto de `1`: quase toda a excitação foi capturada com sucesso;
- `eta(T)` perto de `0`: o transporte foi ruim.

## 10. O que é o loss

Além do `sink`, colocamos também um canal de `loss`.

Ele representa:

**perda parasita**

ou seja:

- parte da excitação foi embora,
- mas não chegou onde queríamos.

Então a distinção é:

- `sink`: sucesso;
- `loss`: fracasso dissipativo.

Isso é importante porque não basta saber que a população sumiu do grafo. Precisamos saber:

- ela sumiu porque foi para o destino certo?
- ou porque se perdeu?

## 11. O que é o trap site

O `trap_site` é o nó do grafo que está ligado ao `sink`.

Ou seja:

- a excitação precisa chegar nesse nó;
- a partir daí, ela pode ser capturada pelo sink.

Então:

- `initial_site`: onde a excitação começa;
- `trap_site`: o nó que alimenta o sink.

## 12. O que os gráficos principais mostram

### 12.1. Sink efficiency by graph

Esse é o gráfico principal.

No eixo horizontal:

- `gamma_phi`, a taxa de dephasagem.

No eixo vertical:

- `eta(T)`, a eficiência final de transporte para o sink.

Como ler:

- se a curva sobe quando `gamma_phi` aumenta um pouco, a dephasagem ajudou;
- se a curva cai, a dephasagem atrapalhou;
- o máximo da curva diz qual regime foi melhor.

### 12.2. Population dynamics by graph

Esse gráfico mostra:

- `P_i(t) = rho_ii(t)` para cada nó;
- e também `P_sink(t)`, a população acumulada no sink.

Como ler:

- mostra por onde a excitação passa;
- mostra se ela oscila entre nós;
- mostra se ela fica presa;
- mostra se ela vai sendo capturada pelo sink.

### 12.3. Coherence by graph

Esse gráfico mostra uma medida agregada de coerência:

```math
C_{\ell_1} = \sum_{i\neq j} |\rho_{ij}|
```

Como ler:

- valores altos: a dinâmica ainda é bem quântica/coerente;
- valores baixos: a dephasagem destruiu grande parte da coerência.

## 13. Como interpretar as animações

Nas animações:

- cor do nó: quanta população está naquele nó;
- tamanho do nó: também codifica a população;
- `S`: sink;
- `L`: loss.

As caixas de texto mostram:

- tempo `t`;
- dephasagem `gamma_phi`;
- `rho_ss`: população no sink;
- `rho_ll`: população no loss.

Então a animação serve para você ver:

- a excitação andando;
- a captura no sink;
- a perda;
- e o papel visual da topologia.

## 14. Trilha pedagógica sugerida

Eu organizei três simulações simples para você aprender em etapas.

### Passo 1: passeio coerente mais simples

Arquivo:

```text
configs/transport_learning_step1_walk.json
```

Ideia:

- cadeia de 2 nós;
- sem sink ativo;
- sem loss;
- sem dephasing.

O que você deve observar:

- a excitação oscila de um nó para o outro;
- isso é o passeio coerente mais básico.

### Passo 2: introduzindo o sink

Arquivo:

```text
configs/transport_learning_step2_sink.json
```

Ideia:

- cadeia de 3 nós;
- agora existe sink;
- ainda sem dephasing.

O que você deve observar:

- a excitação caminha pela cadeia;
- quando chega no trap site, pode ser capturada pelo sink;
- a população no sink cresce no tempo.

### Passo 3: introduzindo dephasing

Arquivo:

```text
configs/transport_learning_step3_dephasing.json
```

Ideia:

- grafo completo de 4 nós;
- com scan de dephasing.

O que você deve observar:

- a eficiência não precisa ser melhor em `gamma_phi = 0`;
- às vezes uma dephasing intermediária ajuda o transporte;
- isso é um dos fenômenos centrais do projeto.

## 15. Como rodar a trilha completa

Existe um script para rodar os três passos:

```powershell
cd "C:\Users\Pedro Henrique\Downloads\Assyntrax-main\repos\Quantum-systems"
$env:PYTHONPATH='src'
python scripts\run_transport_learning_path.py
```

Ou pelo VS Code Task, se eu abrir isso para você.

## 16. O que eu acho que você deve fazer agora

Minha recomendação é:

1. olhar primeiro o passo 1;
2. entender só:
   - nó,
   - aresta,
   - população,
   - oscilação coerente;
3. depois ir para o passo 2 e entender o `sink`;
4. só depois olhar dephasing e coerência.

Se você tentar absorver tudo de uma vez, vai ficar pesado mesmo.

O caminho certo é:

**passeio coerente -> sink -> dephasing -> comparação entre topologias**

Esse é o jeito mais limpo de aprender esse lab.
