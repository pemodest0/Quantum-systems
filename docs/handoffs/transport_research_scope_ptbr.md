# Escopo Real Da Pesquisa Em Transporte Quântico Aberto

Este texto existe para evitar duas coisas:

1. vender o projeto como algo maior do que ele é;
2. ficar abstrato demais e perder o domínio do que estamos fazendo.

## Frase curta do projeto

Estamos estudando **como uma excitação se move em redes finitas sob dinâmica quântica aberta** e perguntando:

**a topologia da rede, a posição do alvo e o ruído do ambiente mudam a chegada ao alvo de forma sistemática?**

## Área delimitada

O projeto está dentro de:

- sistemas quânticos abertos;
- transporte quântico efetivo;
- redes finitas/tight-binding;
- comparação entre dinâmica quântica aberta e controle clássico.

O projeto **não** está, por enquanto, dentro de:

- simulação microscópica realista de materiais;
- modelagem completa de fotossíntese;
- modelagem realista de supercondutores;
- hardware quântico experimental específico;
- temperatura detalhada, banho térmico completo ou não-Markovianidade forte;
- prova de fase da matéria;
- teoria geral de todos os grafos.

## O que exatamente modelamos

Usamos um modelo efetivo com:

- uma única excitação;
- rede finita de sítios;
- Hamiltoniano do tipo tight-binding;
- desordem estática nas energias locais;
- embaralhamento de fase local (`dephasing`);
- perda;
- um canal de chegada (`sink`) ligado a um nó-alvo.

Em linguagem simples:

- o grafo diz por onde a excitação pode circular;
- as arestas dizem quais sítios trocam amplitude;
- o alvo é o ponto onde queremos capturar a excitação;
- o ambiente pode tanto atrapalhar quanto, em alguns casos, destravar o transporte.

## Perguntas centrais que hoje fazem sentido

Estas são as perguntas certas para o estado atual do projeto:

1. **Mudar só a posição do alvo muda fortemente a chegada?**
2. **Existem regimes em que um ruído moderado ajuda a chegada ao alvo?**
3. **A dinâmica quântica aberta carrega informação sobre a família da rede além do que uma caminhada clássica explica?**
4. **Quais observáveis de mistura e espalhamento ajudam a interpretar a dinâmica sem serem confundidos com eficiência?**

## Observáveis centrais

Os observáveis que realmente sustentam o projeto são:

- `arrival`: quanto chegou ao alvo;
- `hitting time`: quão rápido o alvo é atingido;
- `quantum minus classical`: diferença entre chegada quântica e clássica no mesmo grafo;
- `dephasing gain`: quanto um ruído moderado melhora ou piora a chegada.

Os observáveis de diagnóstico são:

- coerência;
- entropia de von Neumann;
- pureza;
- entropia de Shannon populacional;
- participation ratio / IPR;
- MSD / front width quando há coordenadas.

Regra importante:

**entropia, espalhamento e coerência ajudam a interpretar o mecanismo, mas não substituem chegada ao alvo.**

## O que já está forte hoje

Pelos resultados atuais do laboratório:

- a **posição do alvo** é uma variável central, não um detalhe técnico;
- existem famílias com **chegada quântica maior que a clássica** com margem estatística positiva;
- existem regiões com **dephasing-assisted transport** em campanhas não-smoke;
- a **classificação de redes por assinatura dinâmica** funciona acima do acaso;
- a suíte por paper já funciona como guarda-corpo metodológico.

Em outras palavras:

o projeto já tem pergunta, método, observáveis, controles e achados reais.

## O que ainda não está fechado

Também precisamos ser honestos:

- o atlas global completo ainda não foi confirmado em perfil forte/intenso;
- várias fronteiras entre famílias e regimes ainda precisam de amostragem maior;
- fractais ainda são uma frente exploratória;
- materiais reais continuam só como motivação, não como claim.

## Formulação humilde e boa para o professor

Uma formulação segura é:

> Meu foco não é simular um material real em detalhe. O foco é entender, em modelos efetivos de redes quânticas abertas, como topologia, posição do alvo, desordem e ruído mudam a chegada ao alvo e a assinatura dinâmica do transporte.

Outra formulação boa:

> A ideia é construir um laboratório computacional controlado para separar o que vem da rede, o que vem do ambiente e o que realmente é vantagem da dinâmica quântica aberta em relação ao controle clássico.

## O valor científico real

O valor do projeto não está em “simular tudo”.

O valor está em:

- montar um laboratório reproduzível;
- comparar famílias de rede sob o mesmo protocolo;
- separar eficiência de transporte de mero espalhamento;
- impor controle clássico;
- impor comparação com papers;
- mostrar onde o ruído ajuda e onde não ajuda.

Isso é um projeto de mestrado forte porque junta:

- física aberta;
- redes;
- simulação numérica;
- análise estatística;
- leitura crítica da literatura.

## O que não dizer

Evite estas frases:

- “estamos simulando materiais reais”;
- “provamos o mapa de fase completo”;
- “entropia alta significa transporte melhor”;
- “o quântico sempre ganha do clássico”;
- “o ruído ajuda sempre”;
- “resolvemos classificação de grafos em geral”.

## O que dizer

Prefira:

- “estamos trabalhando com modelos efetivos controlados”;
- “alguns regimes mostram ganho quântico sobre o clássico”;
- “o efeito depende da rede, do alvo e do ruído”;
- “a entropia é diagnóstico de mistura, não medida direta de sucesso”;
- “o atlas global ainda está em expansão”.

## Versão de 30 segundos

> Eu estou estudando transporte quântico aberto em redes finitas. A pergunta principal é como a rede, o alvo e o ambiente mudam a chegada de uma excitação a um canal de sucesso. O projeto usa modelos efetivos, compara com caminhada clássica e tenta identificar quando o ruído atrapalha ou ajuda. O resultado mais forte até agora é que a posição do alvo importa muito e que algumas famílias mostram ganho quântico e assistência por ruído em regimes específicos.

## Próximo passo mais importante

O próximo passo decisivo não é inventar mais tema.

É:

- rodar o atlas forte/intenso em chunks;
- consolidar as famílias com ganho quântico robusto;
- refinar onde o ruído realmente ajuda;
- transformar isso em narrativa curta e defensável.
