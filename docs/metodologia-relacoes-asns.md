# Metodologia: relações entre ASNs (ARC)

O ARC (classificador de relações do Arandurapé) infere, para cada par de ASNs com ao menos um ASN brasileiro, se a relação é
provedor → cliente (`p2c`), par (`p2p`), irmão (`s2s`) ou complexa, com nível, probabilidade e a evidência de cada fonte. O código
está em `products/as_relationships/`, os parâmetros em `config/as_relationships.yaml` e os campos publicados em
[docs/produtos/as_relationships.md](produtos/as_relationships.md). O guia do desenvolvedor descreve entradas, etapas e saídas; este
texto registra **os princípios, a calibração, os limites e as referências**, que valem para qualquer mudança futura no algoritmo.

## Princípios

- **Relação é inferência rotulada**, com nível, probabilidade, fontes e data. Nunca se exibe "provedor" sem o nível; `declarado`
  é só para o ASPA. A interface diz "provedor inferido" e "não são contratos".
- **Evidência primeiro, modelo depois.** Regras determinísticas de alta precisão formam o rótulo (v1); o modelo probabilístico
  (Naive Bayes da v2) só refina: abstém (`sem_classificacao`, posterior < 0,5) e rebaixa, **nunca promove** acima do nível da v1
  (`cap_v1`). Medido: promovendo, o modelo perdia precisão.
- **Cada fonte entra com o seu modelo de erro**, aprendido em dados rotulados (por exemplo, P(rótulo do CAIDA | classe)), e não
  com peso suposto. O CAIDA é prior e régua, nunca verdade; irmãos por CNPJ ou por organização do CAIDA são cadastro, não
  comportamento de roteamento, e não entram no modelo.
- **O nível exige fontes independentes** (ASPA, rampa dos route servers, coletores, clique do topo). CAIDA e irmãos sozinhos nunca
  passam de `possivel`. O ASPA é evidência de alto peso, **não veto**: a disputa vai para `evid.contra`.
- **IPv6 e IPv4 separados.** Divergência forte entre as famílias vira `complexa` (híbrida ou inversa), que não conta como provedor,
  cliente, evento nem cone.
- **Grafo p2c acíclico** por família, com irmãos colapsados: o elo mais fraco de um ciclo é rebaixado, nunca um `declarado`.
- **Histerese.** Mudar de estado exige `persistencia` gerações de evidência (coletas semanais distintas) com a mesma proposta; dois
  snapshots diários sobre a mesma coleta não contam. ASPA positivo muda na hora.
- **Aditivo.** Campos antigos (`upstreams_*`, adjacência no AS_PATH) seguem como alias deprecado; snapshots já publicados não são
  reescritos.
- **`config/as_relationships.yaml` é semântica:** mudar valor muda o significado de `p` e `nivel`; suba `versao` e registre no
  CHANGELOG. O rollback é por configuração (`refino.ativo: false`, `estratos.ativo: false`).

## Calibração e régua

- A régua (`python -m products.as_relationships.validacao --date AAAA-MM-DD`) roda o algoritmo **sem o ASPA como entrada** e mede
  precisão e recall (Brasil e global, nível "≥ provável"), calibração por faixa de `p`, subconjuntos difíceis, retirada de PTT ou
  coletor e estabilidade entre snapshots. O painel (`scripts/scorecard.py`) lê o resultado em `data/ops/relacoes/`.
- A probabilidade do modelo não ficou calibrada globalmente (o Naive Bayes supõe independência entre características
  correlacionadas). Por isso a **`p_calibrada` é por estrato de evidência independente**: é a taxa de acerto observada contra o
  ASPA, por validação cruzada por ASN, e só existe nos estratos `ambos` (CAIDA concorda com o sentido e a tripla confirma) e
  `so_caida`, com pelo menos um ponto de observação (`vps > 0`). Meta: ECE ≤ 0,10 dentro desses estratos; o ECE global não é meta.
  Estratos com menos de 30 eventos não têm ECE.
- Fora do estrato, o elo fica com o nível e o rótulo "sem evidência independente"; `p2c` provável em `conflito` ou
  `sem_evidencia` é publicado como `possivel`. `scripts/conferir_estratos_snapshot.py` confere rebaixamento, cobertura de
  `p_calibrada` (piso de 70% dos p2c ≥ provável do Brasil, por família) e estabilidade de um snapshot publicado.
- **Estabilidade** (com o conjunto de coletores fixo): mudança de classe ≤ 2% dos elos presentes nas duas datas; Jaccard dos
  provedores ≥ 0,95; entradas e saídas ≤ 3% por sentido.
- **O conjunto de coletores é fixo.** A precisão contra o ASPA mudou 8 pontos de um dia para o outro quando a coleta passou de 6
  para 8 coletores. Mudar o conjunto exige medir antes e depois sobre a mesma entrada, e registrar.
- Toda comparação de precisão e recall usa o piso **da mesma data e do mesmo conjunto de coletores**.

## Limites e riscos

| Risco | Cuidado |
|---|---|
| ASPA pequeno, defasado e enviesado para "bons cidadãos" | calibrar com ele, mas não tratar ausência de ASPA como negativo; as medidas contra ele são limites, não verdades |
| Circularidade: CAIDA e tripla vêm dos mesmos coletores que o ARC | são independentes do prior de distância ao clique, não dos dados de caminho; a referência independente é só o ASPA. Rebaixamentos decididos por uma régua são medidos pela mesma régua: revalidar em outra data |
| Rampa dos route servers | vazamento de membro, trânsito comprado via RS e *poisoning*: peso por membro, suporte mínimo e cruzamento com ASPA, CAIDA e coletores |
| IPv6 | o CAIDA cobre bem menos os "upstreams" IPv6 do Brasil que os IPv4: inferir por família |
| Irmão por CNPJ | falso positivo possível (sócio pessoa física com CPF mascarado): só como `possivel` |
| Linguagem pública | "provedor" tem peso comercial e regulatório: níveis e ressalva sempre visíveis |
| Licenças de código de terceiros | ProbLink e TopoScope são BSD-3: reimplementar o núcleo com cabeçalho SPDX e usar o código de referência só como oráculo de teste |

Fora do algoritmo atual, por decisão: feedback de operadores ("esta relação está correta?"), que exige canal de escrita
autenticado, moderação e direito de resposta; elos ocultos (TopoScope, *detour couples*), que só fazem sentido com a régua
estável; a política de `import`/`export` do IRR, que exigiria reparsear o dump bruto.

## Referências

- Gao, L. *On Inferring Autonomous System Relationships in the Internet*. IEEE/ACM ToN 9(6), 2001. DOI 10.1109/90.974527.
- Dimitropoulos, X. et al. *AS Relationships: Inference and Validation*. ACM CCR, 2007. <https://arxiv.org/abs/cs/0604017>
- Luckie, M., Huffaker, B., Dhamdhere, A., Giotsas, V., claffy, kc. *AS Relationships, Customer Cones, and Validation*. IMC 2013.
  <https://www.caida.org/catalog/papers/2013_asrank/>
- Giotsas, V., Luckie, M., Huffaker, B., claffy, kc. *Inferring Complex AS Relationships*. IMC 2014.
  <https://www.caida.org/catalog/papers/2014_inferring_complex_as_relationships/>
- Jin, Y. et al. *Stable and Practical AS Relationship Inference with ProbLink*. NSDI 2019.
  <https://www.usenix.org/conference/nsdi19/presentation/jin> · código <https://github.com/YuchenJin/ProbLink>
- Feng, G., Seshan, S., Steenkiste, P. *PARI: A Probabilistic Approach to AS Relationships Inference*. 2019.
  <https://arxiv.org/abs/1905.02386>
- Jin, Z. et al. *TopoScope: Recover AS Relationships From Fragmentary Observations*. IMC 2020.
  <https://dl.acm.org/doi/10.1145/3419394.3423627> · código <https://github.com/Zitong-Jin/TopoScope>
- Leyba, K. G. et al. *Cutting Through the Noise to Infer Autonomous System Topology*. INFOCOM 2022.
  <https://arxiv.org/abs/2201.07328>
- *Inferring Multiple Relationships between ASes using Graph Convolutional Network*. 2021. <https://arxiv.org/abs/2107.13504>
- Hao, Y. et al. *PathProb: Probabilistic Inference and Path Scoring for Enhanced and Flexible BGP Route Leak Detection*. NDSS 2026.
  <https://www.ndss-symposium.org/wp-content/uploads/2026-f1691-paper.pdf>
- Azimov, A. et al. *BGP AS_PATH Verification Based on Autonomous System Provider Authorization (ASPA) Objects*,
  draft-ietf-sidrops-aspa-verification (Internet-Draft, não RFC). <https://datatracker.ietf.org/doc/draft-ietf-sidrops-aspa-verification/>
- CAIDA. *The CAIDA AS Relationships Dataset (serial-2)*. <https://catalog.caida.org/dataset/as_relationships_serial_2>
