Foram debatidas diferenças e complementaridades entre métodos não supervisionados (clustering, SOM) e supervisionados (Random Forest, SVM), com Marco ressaltando o distinto objetivo de reorganização versus previsão e propondo um ciclo iterativo de dois semestres útil para modelos supervisionados. Abordaram-se variáveis candidatas (gama, bandas de sensoriamento remoto, relevo, distâncias a estruturas), engenharia de features, balanceamento de amostras para evitar viés entre classes, limites do deep learning e opções de infraestrutura (workstation no IGC, uso de clusters públicos conforme necessidade). Discussões finais trataram da orientação do Trabalho Final de Gabriel, documentação científica (repositório GitHub, relatório/artigo) para atração de supervisores e financiadores, integração com IPT para aplicações territoriais e o uso de ferramentas de IA (Codex, SciSpace) integradas a VSCode/Colab para acelerar desenvolvimento, leitura de codebase e geração de documentação.


6:54 - Gabriel Goes Rocha de Lima
vai ficar falando aqui ele vai transcrição. Bom dia, professor. O senhor colocou o assistente pra conversar comigo? RISOS Sério?

10:49 - Gabriel Goes Rocha de Lima
Tchau.

13:20 - Gabriel Goes Rocha de Lima
E aí Oi, Gabriel. Opa, tudo bem, professor? Opa, tudo bem?

14:16 - Marco Antonio Couto Junior
Cara, me desculpa, eu achei que a gente ia falar pessoal. Essencial, aí eu viajei total. Ah, descobre isso. Viu, perigou isso, né? Eu não me liguei que era online. Oi, tudo bem? Tudo certo.

14:31 - Gabriel Goes Rocha de Lima
Eu achei que o senhor tinha colocado o assistente pra eu conversar com ele e o senhor ia ler a transcrição. Não, não, eu vi seu e-mail, eu falei, nossa, é online.

14:43 - Marco Antonio Couto Junior
Eu tô aqui na sala, eu falei, bom, vou fazendo as coisas e eu cheguei aqui, eu cheguei aqui, né?

14:50 - Gabriel Goes Rocha de Lima
Foi automático, Eu até instalei aqui a transcrição, eu recebi uma mensagem automática aqui desse chat. Então, vamos lá, sem problema.

14:59 - Marco Antonio Couto Junior
Desculpa de novo, cara. Tudo bem, tudo bem.

15:03 - Gabriel Goes Rocha de Lima
Então, eu queria te apresentar esse plugin que eu tô desenvolvendo aqui no QGIS, que eu tô apresentando na minha tela. Daí, tem um tempo assim que eu não mexia nele, desde dezembro do ano passado, que foi quando eu estava fazendo a disciplina da Camila, aí eu estava usando o tempo da disciplina para desenvolver um pouco mais esse meu projeto. E nesse tempo eu consegui criar esse plugin onde eu acesso um banco de dados do meu computador e ele lê as folhas cartográficas disponíveis, então aqui eu tenho, se eu colocar um promilhão, a gente tem todas as folhas do Brasil, e eu baixei todos os dados de mapas litológicos disponíveis na SBG, baixei os pontos de ocorrência, aquelas informações que tem no arquivis online deles. Daí, eu baixei também alguns XYZ, aqueles arquivos de aerogeofísica, e tratei alguns deles, estou tentando desenvolver uma forma de baixar automaticamente e tratar todos eles, mas ainda não consegui. Então, aí o que eu fiz foi, com um teste agora, foi pegar uma folha, que é essa folha da região do Amazonas, é a folha SBXC, daí eu inseri ele num com SB21, XC, Y4, daí eu inseri ela numa rede neural, que é um self-organizing maps, e ele retorna esse mapa, na verdade isso aqui não é um mapa litológico, porque eu não inseri um treino, eu não treinei a rede, ele é apenas uma classificação, uma classificação não supervisionada dos dados, né? Provavelmente ela não está condizente, assim, com a litologia da região, mas foi uma primeira iteração que eu fiz aqui rapidamente, antes da apresentação, e a ideia seria essa, né, a gente pegaria os dados que a gente já tem hoje em dia, cria um mapa preditivo, vai a campo, confere se essas litologias estão batendo com E, a partir desses dados de campo, a gente iria inserir mais dados novos no nosso banco de dados. E, com isso, o mapa preditivo iria modificar com essas informações novas. Daí ele funcionaria dessa forma iterativa, assim. A gente iria para campo, pega o valor...

18:04 - Marco Antonio Couto Junior
Essa seria a ideia, né? Sempre com classificação... Não supervisionada, né? Você está fazendo um agrupamento, né? É isso, é um cluster, um agrupamento.

18:16 - Gabriel Goes Rocha de Lima
Por enquanto, a gente está usando esse não supervisionado, mas eu já utilizei o Random Forest e o Support Vector Machine, que a gente escolhe alguns pontos da área, a gente escolhe os pontos balanceados, porque tem uma distribuição não normal, Classes litológicas tem muito pontos e classes litóricas tem menos pontos. Então a gente teria que escolher pontos de forma balanceada para não enviesar o modelo. Mas eu já utilizei esses dois algoritmos, o RandomForce e o SupportVectorMachine. Então a ideia seria essa, criar uma ferramenta dentro do QGIS que seria de fácil acesso para o pessoal do, por exemplo, o pessoal do mapeamento geológico do quarto ano. Então, eles poderiam utilizar essa ferramenta, antes de ir para a primeira etapa do campo, aí eles iriam para o campo, coletavam informações, inseriram no banco de dados, aí na segunda etapa de campo, no outro semestre, eles já teriam um mapa melhor ainda. Então, essa iteração seria possível de fazer esse teste, né? Porque a gente tem duas etapas de um campo, então mapa a prévio, gente antes teria da primeira etapa, é um mapa depois da primeira etapa de campo e um mapa depois da segunda. Então seria uma forma de testar essa iteração duas vezes.

19:51 - Marco Antonio Couto Junior
É, acho que isso funciona bem somente para o supervisionado, né? Bom, não supervisionado eles teriam talvez que gerar o mapa antes, né? E ver como o som reorganiza essas coisas. Sim. E você acha que com o não supervisionado ele não iria funcionar tão bem? Não, eu acho que sim, porque como o pessoal vai a campo, aí eles vão ter os pontos, os reafloramentos, e aí você está tentando prever. O supervisionado é uma previsão, uma coisa que vai que você está tentando prever no futuro. O Som, ou outro algoritmo de agrupamento, de clustering, Camins, eles estão tentando reorganizar a informação, achar padrões que eu consiga reorganizar a informação, certo? E o supervisionado, não. Ele está com base no que ele tem, ele tenta prever onde não tem. Aí, com novos pontos, de afloramento, novos pontos de campo. Isso você aumenta a sua base de treino, né? Que aí sim você vai ter que treinar novamente. Isso. Aí eu acho que isso é bem importante, sim, para o supervisionado. Que aí essa interação que eles têm de dois semestres, né? Tipo, primeiro a gente fez esse pré-terminado, aí foi para o campo, xipou, aí falou, não, aqui, está vendo? Estava prevendo que era essa unidade, na verdade, a gente tem toda essa região que é uma coisa diferente. Então, aí eles modificam, aí eles voltam, reclassificam, e aí com essas novas informações, eu acho que o treinamento vai melhorando. Sim. Então, eu acho que é massa. E para o clustering, basicamente, para o som, aí assim, para eles poderem comparar, eles teriam que partir de um mapa geológico. Ou, você tem que ter um raster, você vai ter que rasterizar alguma coisa para ele poder trabalhar. Ele poderia rasterizar um mapa geológico e aí ele vê como ele organiza. E depois que... Que fizer o novo mapa geológico, depois que eles forem a campo e voltarem e fizerem um novo mapa, aí fazer de novo esse agrupamento com as novas informações. É que eles são objetivos bem distintos. Um, que é o não supervisionado, você está tentando organizar as informações de maneira que elas tenham coerência entre as simples, que a gente agrupa, né? E aí, eu acho que o novo mapa, assim, um poderia ser um check do outro, pra ver se eles fazem sentido. O novo mapa seria de volta com o clustering, pra você ver se aquelas informações que você tinha antes, na forma de agrupar, elas mudaram. E o supervisionado é uma coisa uma coisa que você está tentando prever, onde seria útil. Locais que eles não conseguiram acessar, que eles têm poucos pontos de afloramento. Porque ali não tem difícil acesso e tal. Ali pode ser uma coisa interessante, porque já que eu não conseguia andar muito bem lá, o meu modelo preditivo, ele deveria ter uma certa capacidade de generalizar lá com os padrões Aí seriam dois produtos, coisas complementares. Um preditivo e um que você vê, realmente, eu vejo que um agrupamento, um cluster aqui, ele agrupa isso tudo com não uma unidade biológica, mas como um cluster, um grupo. E aqui parece que esse grupo está relacionado a tal unidade. Aí você vê no mapa preditivo. Produtos sociais e complementares, né?

24:11 - Gabriel Goes Rocha de Lima
Seria aquela diferença, seria a diferença entre o interpolador e um generalizador, né? Seria, por exemplo, quando você só quer pegar informações entre um ponto e outro que você não mostrou, aí você está interpolando. É, você poderia... Se não atingiu uma área, tem uma área que está dentro de um vale, com muita vegetação, você não conseguiu chegar lá, aí você interpola para aquele ponto.

24:39 - Marco Antonio Couto Junior
Só que essa interpolação do Random Forest, por exemplo, usando o pré-classificar, ela já é uma interpolação mais esperta, ela está tentando prever mesmo. Não é só uma interpolação simples, no sentido de você só especializar aquela informação ali, Ele vai ter que olhar outras camadas, como que está treinando isso, tem que ver, mas está usando a área geofísica, está usando dados de censuramento remoto, o terreno, ele aprendeu com esses padrões. E aí ele tentou prever aquele pixel lá no vale que você não conseguiu entrar, não deu. E aí ele preveu de uma maneira mais esperta do que um interpolador simples. Até falando de Krigaras, que é com base... É probabilidade também, mas é outra previsão, mas... Um algoritmo tipo Random Forest ou SDN, até uma rede neural, Ele está tentando, de fato, previser aquele pixel com base no que ele aprendeu no entorno. É que aí já é uma outra questão que é o generalizador.

26:10 - Gabriel Goes Rocha de Lima
Por exemplo, a gente treina nessa área aqui, por exemplo, nesse quadrante sudoeste aqui. A gente treina com os pontos daqui e testa para a área inteira. Aí a gente está generalizando as informações que a gente pegou dessa área para a área inteira. Ou então a gente treina com os pontos dessa área que a gente mapeou e testa para a área vizinha, que é ao lado. Aí a gente está generalizando a informação que a gente tem aqui para uma área ao redor.

26:43 - Marco Antonio Couto Junior
Isso. E isso ainda não supervisionado, né? Justamente um modelo bom que a gente almeja ter é bem isso, é um modelo que consiga generalizar informações. Aí a gente tinha que fazer um overfitting. Ele só aprender decorou para aquela área e não sabe mais nada, né? Sim. Aí o outro, o não supervisionado, né, um cluster, assim, você, som, caminho, qualquer outro tipo de algoritmo, aí a coisa é um pouco diferente, né? Você vai alimentar o... Se o modelo com os rastros que você tiver, pode ser os mesmos, tipo assim, área geofísica, estacionamento, terreno, etc. E ele tenta encontrar sinalidade dentro dessas informações que você está colocando e ele organiza isso num espaço, ele vai tentar. Isso aqui eu estou vendo que pertence a um certo grupo, Depois desse outro aqui, parece que... Aí, assim... A gente fala que ele treina, mas o treinamento dele é bem diferente. Não tem toda aquela questão de treino, trein, test, split, você separar. Ele está tentando agrupar, então não é exatamente uma previsão. Ele não vai falar para você, olha, isso aqui, é a unidade A, isso aqui é a unidade B, isso aqui é a unidade C, ele vai falar, ó, aqui tudo parece como um grupo muito semelhante entre si.

28:23 - Gabriel Goes Rocha de Lima
Sim, ele é direcionado para os dados, ele só observa os dados, ele não vai entender sobre o que é uma classe e o que é outra classe, no sentido de que a rocha específica é outra, a gente não treinou ele nesse sentido, ele só está falando, ah, esses pontos aqui são muito similares nesse campo multidimensional que a gente está criando. Então, ele agrupa. Isso aí, isso aí.

28:49 - Marco Antonio Couto Junior
Aí, eu acho que os dois, trabalhando com os dois juntos, tanto o supervisionado quanto o não supervisionado, é uma coisa que elas complementam. Um, de fato, a gente está fazendo uma previsão. Olha, eu fiz um SVN aqui, e aqui nesse ponto, Era um granitão. Aí, no clustering, no som, a gente vai ver, olha, fato, aqui no granitão tem um clustering bem característico, e aí a gente começa a ver. Olha, tá vendo que o modelo preditivo também previu que outras regiões aqui podem ter outros granitos semelhantes a esse, e aí a gente, tipo, gostaria de ver, né, na situação ideal. Quando eu olho no cluster, eu vejo que aquele grupo que pegou um granito bem característico, o grupo se espalha em outros pontos onde a gente está achando que tem granito. Não é uma sobrefusão, eu não espelharia que fosse perfeito, mas a gente vê coerência entre os dois. Faz sentido. Por isso que eu estou tratando que para o pessoal do mapeamento, Quando eles voltarem no segundo semestre e forem fazer um segundo mapa, depois para dar um som novamente, eles poderiam até usar como check. Realmente, a gente vê coisas que são semelhantes, que mudam. Era legal fazer o antes e o depois, tipo uma fotografia no tempo. Era assim, ficou assim, com a informação nova, porque a gente, depois refez o mapa e reabrocou de novo. Então, eu acho que seria massa. Mas eu acho que é sim. Pode falar. Eu dei uma liga lá no GitHub de vocês e sim, cara, eu acho massa a ideia. Então assim, agora o projeto ele tá nessa parte dos modelos de machine learning, né? Enquanto não supervisionado, né? Aí você mencionou também que você tem o objetivo de processar tudo de uma vez, num único, num on-the-fly, como é que você está pensando isso aí?

31:16 - Gabriel Goes Rocha de Lima
Eu estava pensando no sentido de ter o banco de dados inteiro, de todo o Brasil, e sempre que alguma instituição ou universidade ou, por exemplo, a CPRM ou uma outra universidade fizesse um campo de mapeamento geológico, ele inseriria essas informações nesse banco de dados e retornaria um mapa preditivo novo. Sempre que alguém da geologia, por exemplo, vamos começar só pelo IGC, sempre que alguém do IGC fosse a campo, inseriria essas informações no banco de dados, em vez de ficar num CSV no computador de cada um, a gente teria um banco, aí na geologia, em que a gente inseriria esses pontos nesse banco e teria como retorno um mapa preditivo. Tanto supervisionado ou não supervisionado, dependendo da situação. A ideia seria essa, né? Que tivesse essa iteração, né? Você vai pra campo, pega novos dados, retorna um mapa. Aí você analisa aquele resultado, valida, e planeja um novo campo direcionando para aquelas regiões de interesse. Aí você vai no campo de novo, seria essa a ideia, assim. E como tem campo todo ano, todo ano tem campo para as regiões mais ou menos as mesmas, isso é muito interessante, porque a gente sempre pode ir validando aquele mapa, né. Sim, sim, sim. Eu tinha tido uma ideia de criar um mapa não supervisionado, usar ele para treinar um modelo supervisionado e testar. Só que eu conversando com o Victor, não sei se você conheceu ele, é o Victor Silva, ele está no Canadá.

33:01 - Marco Antonio Couto Junior
Eu não o conheço pessoalmente, mas eu sei quem é.

33:05 - Gabriel Goes Rocha de Lima
Ele falou assim, cara, se você treinar um modelo supervisionado com os dados do Self-Organizing Maps, você está no máximo fazendo com que o seu modelo supervisionado crie um mapa igual ao Self-Organizing Maps. Tipo, ele vai se No máximo, ele vai ser igual ao Self-Organizing Maps.

33:24 - Marco Antonio Couto Junior
É, se você só treinar o supervisionado com o resultado do som. E, geralmente, esse faz, né? Você deve ter ouvido falar o termo engenharia de variável, feature engineering, né? Que é engineering, né? Que é, tipo assim, é a parte lá do machine learning, que a gente cria variáveis, né? Melhorar desempenho, melhorar treinamento do modelo. Do modelo supervisionado. Bom, poderia ser clustering também, mas geralmente a galera usa mais para o supervisionado. O que é interessante é assim, e se faz isso, quando você tem um modelo, um clustering, um agrupamento, uma coisa assim, não só usá-lo para treinar, que aí sim, o melhor resultado, que é o ideal, é você chegar de volta no que você já agrupou. Agora, ele poderia ser um variável de entrada junto com as outras, que você utilizaria para uma classificação supervisionada. Que seria o mapa biológico da CPRM, por exemplo.

34:37 - Gabriel Goes Rocha de Lima
Por exemplo.

34:38 - Marco Antonio Couto Junior
Não só o resultado do cluster, mas o mapa da CPRM Aí, mais dados aerogeofísicos. Aí a gente começa, até fazer uma razão nos dados de gama. Razão entre os canais, potássio-sorbitório, isso já é fit in theory. Se você pensa para um modelo de machine learning, porque o que a gente está fazendo, por exemplo, quando calcula a razão, potássio-sorbitório? Estou tentando ver um enriquecimento anômalo de potássio na crosta, porque a gente fala Então, isso já seria. Aí, pô, o relevo importa, importa. Vou entrar só com o modelo editório terreno? Será que a declividade também é interessante? Depende do que você está estudando, né? Tipo assim, o que você quer prever, né? Se for um mapa geológico...

35:30 - Gabriel Goes Rocha de Lima
Pelo que eu vi, a feature engineering mais importante para a geologia são as distâncias. Você pega a distância para uma estrutura. Distância para alineamentos magnéticos, distâncias para falhas. Isso aí, isso aí. É, assim, é sempre...

35:46 - Marco Antonio Couto Junior
Isso é um negócio da machine learning, assim, o que você vai treinar, para que você vai treinar, né? Assim, para que você vai treinar, então, isso implica no que você vai jogar para alimentar o modelo, né? Então, assim, se é mapa mediológico, Bom, quais são os dados que eu tenho que me ajudariam muito? Gama eu acho que é um negócio que me ajuda, porque a gente vê que tem muita correspondência. Dados de sincroniamento remoto, bandas do suído, do infravermelho, o shortwave, o próximo, o near. Então, será que isso também me ajuda? Acho que me ajuda. A primeira coisa que a gente tem que ver, que é a primeira coisa que tem que ver mesmo, se o que eu quero usar para prever, ele tem uma correlação clara com o que eu quero prever. Então, se as litologias têm correlação com essas variáveis, então, são bons parâmetros para entrar para fazer a previsão. Aí, por isso que o Clang, Bom, já assim, assumindo, exemplo, né, assumindo que, olha, a gama tem correlação, os dados de censuramento apresentam correlação. Pô, eu estou em uma região montanhosa, então, sei lá, tem correlação, assim, morro com granito, morro com informações períferas, né, então eu estou vendo que tem. Então isso tem correlação. Então eu vou entrar no modelo digital de terreno adequado E aí, essas coisas, eu consigo prever. O clustering, se você fizer o clustering com isso, vai acabar sendo que ele tem correlação com o que você quer prever, porque você já viu que as outras que você usou para fazer o clustering têm correlação. Então, é esperado isso. E aí, você faz mais uma variável. E dá para dar importância para as variáveis. Também, né, em treinamento. Então, às vezes você fala, pô, não quero enviesar muito pelos resultados. Eu quero usar o Puzzle, não quero enviesar. Então, você poderá isso também, alguns do algoritmo. Depende do algoritmo, né? Então, dá para você...

38:13 - Gabriel Goes Rocha de Lima
A ideia do Deep Learning seria inserir o maior número possível de features, né? E o próprio modelo iria colocar um peso para a feature. Então, você poderia colocar, por exemplo, até informações sobre deslizamento de terra, regiões onde houve deslizamento. Talvez isso fosse importante para prever algum tipo de litologia que está condicionando aquele deslizamento. Então, quanto mais informações, talvez fosse... O próprio modelo vai colocar o peso da importância.

38:45 - Marco Antonio Couto Junior
No Deep Learning, é mais difícil de controlar isso, porque, de fato, no Deep Learning, Deep learning, simplesmente, sim. É uma rede neural com muitas camadas. Aí, assim, é difícil entender. Eu nem manjo tanto da parte de deep learning, mas é mais difícil de entender como é que a ponderação dos pesos ocorre, porque a coisa acontece ali dentro das camadas de forma otimizada, é um processo literalmente de otimização numérica, que vai ajustando esses pesos e você vai melhorando o treinamento. Mas é isso. Espera-se que, no fim das contas, o que a rede prevê e os pesos que ela fechar, finalizar o treinamento dela vão dizer para nós o que é mais relevante o que não é. O negócio começa a ficar tão quebrado, não depende de quantas camadas tem, porque a primeira, tudo bem, você pode entrar com os dados físicos, como comissão, terreno, geofísica, saciedade. Depois há coisas derivadas deles, tipo assim, as variáveis são derivadas desses dados, e aí, assim, pô, o que é isso? O que é o escrito treinando nas outras camadas? Então, fica mais difícil de entender. Por isso que eles falam que é difícil entender como que uma rede neural aprende, embora, assim, tenha gente pesquisando isso. Mas eu acho que é massa. Mas é isso que você falou. Ah, assim, O projeto é sensacional.

40:32 - Gabriel Goes Rocha de Lima
A ideia seria pegar esse programa que eu estou desenvolvendo no meu computador pessoal e levar para o computador do IGC, porque tem um computador no IGC que é uma workstation. Eu não sei qual é o sistema que ele está operando, mas a Camila tinha esse computador no laboratório de inteligência artificial.

40:58 - Marco Antonio Couto Junior
Eu já fiz assessoramento remoto.

41:00 - Gabriel Goes Rocha de Lima
É o computador, é o laboratório que está embaixo da OLIG, né?

41:04 - Marco Antonio Couto Junior
Isso, eu divido com ela, sou eu e ela. É o nosso, é a minha ideia.

41:11 - Unidentified Speaker
Legal.

41:11 - Gabriel Goes Rocha de Lima
Aí a ideia é você levar esse computador, esse programa que eu estou desenvolvendo, para aquela máquina. É. Instalar um...

41:20 - Marco Antonio Couto Junior
Large, que dá para rodar. Ele é uma workstation, ele não é um cluster. Mas o computador já comparado a esses desktops de bancada, os comuns que têm escritório, já é bem melhor. Dependendo da complexidade de você, se você partir para a parte de deep learning, que aí vai precisar de bastante poder computacional, existem opções de clusters públicos, pois eu até te mando que como instituição de pesquisa universitária, a gente tem acesso. Tem rede federal, rede estadual. Tem o LNCC, tem o...

42:04 - Gabriel Goes Rocha de Lima
Até o próprio Intra, eu acho que tem um cluster deles, né? A Poli. Isso. Sim. Então, a gente...

42:14 - Marco Antonio Couto Junior
Isso é uma coisa que pode ser Claro, vai ser para depender da complexidade, o que você quer fazer.

42:23 - Gabriel Goes Rocha de Lima
A minha ideia, primeiro, seria fazer algo dentro do IGC, mesmo sem deep learning, algo mais complexo, fazer uma rede neural, talvez, ou usar um self-organizing maps, ou um random forest, dentro dessa workstation do IGC. Daí, se estivesse funcionando bem, a gente poderia passar para um próximo de usar um cluster. Ah, tá. Acho que é por aí.

42:50 - Marco Antonio Couto Junior
E isso é o quê? É o seu projeto pessoal? Você vai fazer um tráfico nisso? Como é que... Você ainda não se formou, né? Você tá no...

43:01 - Gabriel Goes Rocha de Lima
Isso, isso. Tô fazendo Geologia Econômica e Gênero de Depósitos. Tô fazendo duas disciplinas optativas, com a Camila e com o Renato. É Machine Learning e Análise de Dados. Mas, então, esse projeto, eu comecei em 2021 com o Caetano, a gente, com a iniciação científica, eu fiz dois anos, só que aí no terceiro ano de iniciação científica, eu fui para o IPT, em 2023, aí eu tô lá até hoje como estagiário, daí eu fui tocando esse, eu fui tocando esse projeto em casa, assim, em paralelo, só que eu não estava tendo muito tempo para focar nele, porque o estágio estava tomando muito Daí, a minha ideia seria de transformar o meu estágio no IPT nesse projeto. Então, trazer esse projeto do IGC para o IPT, só que com um viés do que o IPT precise. Então, eu estou entrando em contato com algumas pessoas, por exemplo, lá no IPT a gente faz mapeamento territorial, planejamento territorial minerário. E também tem mapeamento de deslizamento de terra. Então, a gente poderia utilizar essa ferramenta para esses mapeamentos. Então, prever deslizamento de terra, prever enchentes, ajudar no planejamento territorial. Então, essa seria a minha ideia, de utilizar essa minha ferramenta dentro do IPT em conjunto com o IGC.

44:35 - Marco Antonio Couto Junior
Existe algum projeto de pesquisa lá dentro do IPT para isso? Você está envolvido?

44:44 - Gabriel Goes Rocha de Lima
Então, tem alguns projetos de pesquisa, tem pesquisadores, pesquisador assistente lá, pesquisador visitante, mas eu não estou envolvido neles diretamente. Eu estou na sessão de obras civis, eu trabalho com sismologia e eu faço o monitoramento das barragens, com sismos induzidos. Só que aí eu tô migrando agora para as outras áreas para fazer geomodelagens das barragens, mas a minha ideia seria ir para essa área de planejamento territorial, para eu poder aplicar esse meu projeto. Então, eu vou tentar encontrar uma forma de conectar o IGC com o IPT, de projeto de pesquisa. O Caetano falou que eu não deveria focar nisso, porque é uma burocracia bem grande de tentar criar um projeto entre instituições. É, isso ele tem razão.

45:53 - Marco Antonio Couto Junior
O que eu acho que... Uma sugestão que eu faria, que eu faço para você, você está ano, então que vem você vai ter que fazer um TF, né? Isso. Esse é um tema muito bom do seu TF. Então, assim, isso também vai te forçar a documentar isso que você tá fazendo. Tem o GitHub, que já tá excelente, pelo que eu vi lá. Mas e ter um... Quando eu falo documentar, é um documento científico mesmo, né? Poderia ser um artigo, né? Mas lá pra frente, mas uma coisa que você vai ter para mostrar, para vender sua ideia. Isso é importante também. Então, você ter isso organizado, essas ideias, metodologias, que é ir lá no GitHub, embora você tenha colocado os scripts lá, os códigos estão lá, quase ninguém para para ler código. A pessoa quer ver uma coisa mais sintética. A metodologia utilizada, o raciocínio, a motivação, por onde vem... Escrever um relatório, né?

47:05 - Unidentified Speaker
É.

47:05 - Marco Antonio Couto Junior
Então, o TF, pensando aqui, bem pragmaticamente, né, do ponto de vista de tempo, o quanto você vai ter para dedicar, ele meio que te força, porque você já vai ter que fazer o TF de todo jeito. Então, você já vai fazer ele direcionado a isso. A primeira sugestão que eu faço. Seria uma ideia muito boa, o tema de ETF fantástico, vamos perder muito apelativo, muito apelativo e promissor. Lá para frente, eu não sei como está a relação com a IPT, você disse que está conversando para mudar para a área de risco de deslizamento, né?

47:54 - Unidentified Speaker
Isso.

47:54 - Marco Antonio Couto Junior
Eu não sei, quem que é o supervisor lá de estágio? Por enquanto é a Sofia e o Wilson.

48:02 - Gabriel Goes Rocha de Lima
O Wilson, nossa, não sei se você conhece, o Wilson é geólogo aqui da USP.

48:09 - Marco Antonio Couto Junior
Tá, tá. É, eu acho que assim, com o tempo, você tá começando o quarto ano agora, então você tem mais, na prática, dois anos aí, né, pra... Mais do estágio, eu acho que é uma coisa que você tem que ir conversando com eles. Bom, eu tenho essa vontade, né?

48:30 - Gabriel Goes Rocha de Lima
Mas assim, com cuidado, né?

48:32 - Marco Antonio Couto Junior
Não sendo uma coisa impositiva, né? Um negócio... Eu acho que é bem legal você mostrar pra eles, ó, eu tenho essa vontade de se mover nessa área. Menciona que você tá fazendo esse tipo de trabalho, mas assim, sempre... Como uma relação de trabalho, então sempre nada impositivo, né? Fala o que você quer no futuro e direcionar para isso. E aí acho que esse seria o primeiro passo. Primeiro assim, você documentando e conversando o que você quer, e se você já conseguir logo de cara migrar, aí show de bola, né? Porque conforme você vai documentando, e aí você pode linkar isso para o seu trabalho, as atividades que você vai fazendo que você pode mostrar as coisas para eles, né? Que, vamos lá, eu estou trabalhando nisso, estou fazendo isso, já consegui chegar até aqui, meu plano é os próximos passos, eu estou querendo expandir em termos de opções de modelo, estou pensando aqui na parte de deep learning também, etc. E aí você vai vendendo isso. Aí pode ser, não é nada que a pesquisa do governo é garantida, que pode ser que isso desperte o interesse, né? Porque às vezes chegar... As pessoas ficam tão imersas na sua rotina, né? Que às vezes você chega não, e pô, diz, podia fazer um projeto e tal. Aí o cara, pô, cara, mais... Às vezes tem um monte de como fazer. Mais uma coisa para resolver no meu dia, o cara... Tá, depois a gente conversa.

50:10 - Gabriel Goes Rocha de Lima
Conversando com o Gamba, conversando com o Gamba lá do IPT, ele demonstrou... Eu fiz uma reunião com o Gamba, um gerente da minha sessão, e o Iago Costa, que é o coordenador de geofísica da CPRM. Eu apresentei esse meu projeto para o Iago, o Iago demonstrou bastante interesse, só que a CPRM não conseguiria financiar esse projeto, ele não tem um edital para financiar. Eles entrariam em um edital junto com a gente, assim, com a Finep ou qualquer outro edital. Só que o Gamba, nessa apresentação, ele demonstrou bastante interesse nesse meu projeto, ele até me convidou para ir trabalhar com ele, só que eu sou de outra sessão, então eu não poderia migrar para a sessão dele, a não ser que ele abrisse um contrato lá nessa sessão, mas...

51:00 - Marco Antonio Couto Junior
um caminho para ser explorado com ele, já que ele demonstrou interesse. Isso é um negócio que eu falo, não é exatamente uma empresa, um IPT, não é um meio corporativo, por assim dizer, mas acho que no trabalho você sempre tem que deixar claro, deixar muito claro para os seus superiores quais são as suas opções de carreira. Eu estou aqui para isso, então eu tenho a vontade de desenvolver nisso aqui. E para ter alinhamento de expectativa, porque às vezes o seu chefe está pensando, você está na área de risco sísmico, está envelhendo risco de barragem, às vezes o cara está lá assim, o Gabriel, eu preciso desse cara aqui mais dois anos, porque vai sair um projetão aqui, e às vezes não é a sua ambição. Então, é uma questão de político. Mas, enfim, eu acho que é um caminho a ser explorado com ele. Você ir conversando mais, você ir devagarzinho.

52:07 - Gabriel Goes Rocha de Lima
Eu acho que o primeiro passo agora seria me concentrar nas matérias do quarto ano e no meu TF. Eu já posso começar escrevendo meu TF, por exemplo. Mesmo assim, acho que seria esse o caminho mais comum.

52:23 - Marco Antonio Couto Junior
É, vai organizar. Vocês devem conhecer o Édipo, o Édipo está fazendo TF comigo esse ano aqui, comigo com a Camila. Uma coisa que ele veio aqui na sala ontem, eu até sugeri para ele, uma coisa que eu tento, na loucura do dia a dia, da rotina, quando eu estou num trabalho, num projeto, fazendo as coisas, conforme eu vou fazendo, eu fico com um Google Slides ou um PowerPoint do lado, E aí, ah, eu gerei um resultado novo. Aí, uma figura nova, uma figura importante. Eu vou jogando, vou alimentando aquele PowerPoint lá e eu vou escrevendo algumas coisinhas de ideias, de conclusões. Ó, isso aqui mostra isso e tal. Porque isso me ajuda, cara. Depois, na hora que eu sento pra escrever um relatório, um artigo, um documentário mesmo, cara, isso me ajuda muito. Porque a ideia, às vezes, você esquece. Você vai revisitar uma ideia quatro meses depois. Já foi.

53:24 - Gabriel Goes Rocha de Lima
Imagina um projeto que eu estou tocando desde 2021. Tem um monte de arquivo, um monte de coisa. Eu já comecei do zero várias vezes.

53:35 - Marco Antonio Couto Junior
Exato, exato. Então, abre um PowerPoint no Google Slides, no Google Drive. Vai jogando, direi esse resultado novo. Faz um resuminho, um tópico mesmo. Aqui eu pensei nisso. Treinei uma rede neural para aquilo, pôs esse objetivo, quero prever tal coisa. Olha, variáveis que são importantes para entrar. Aeromag, aerodama, swear, near, mas eu tenho que pegar o slope também, calcular o slope por causa disso. Então, tipo, vai fazendo essas coisinhas que aí vai me ajudando, com certeza isso vai ajudar. E vai, vai esboçando quando entra no... Aqui, eu tenho que caçar isso aqui. Eu vou ter que apresentar para os alunos. Eu também faço parte da CTF, da Comissão de Ensinamento, provavelmente vão fazer um documento dos TEFs, né? Tem os guidelines e as etapas. Que você vai ter que entregar um monte de coisas. A primeira coisa que você tem que entregar é o projeto inicial. Aí tem os guidelines lá para o projeto inicial. Aí depois tem um projeto... É tipo uma parte que você tem que entregar um relatório de andamento, que é no meio da coisa. Entrega três grupos.

55:03 - Gabriel Goes Rocha de Lima
Aí depois você tem que entregar isso.

55:06 - Marco Antonio Couto Junior
E depois você tem que entregar a monografia propriamente E aí tem os guidelines de cada coisa. Eu vou ver aqui... Se conseguem me enviar algum arquivo desses?

55:17 - Gabriel Goes Rocha de Lima
Mesmo que eu não esteja manipulado no TF? Ah, não.

55:21 - Marco Antonio Couto Junior
Isso aqui é aberto. Está no site do IGC. Vou procurar. Aí eu vou... Te mando isso aqui. Certo. Qualquer coisa eu procuro também.

55:30 - Gabriel Goes Rocha de Lima
Se está no site do IGC eu acho que eu consigo encontrar. Qual é a opinião do senhor quanto a... Ferramentas de IA.

55:39 - Marco Antonio Couto Junior
Pode me chamar de você, tá?

55:43 - Gabriel Goes Rocha de Lima
Eu não tenho 40 anos ainda.

55:46 - Marco Antonio Couto Junior
E não estou com essa ideia, não.

55:50 - Gabriel Goes Rocha de Lima
O que você pensa sobre as ferramentas de IA? Por exemplo, o Codex?

55:57 - Marco Antonio Couto Junior
Codex eu nunca usei. Coisas que eu tenho feito na vida, Python, E eu uso também softwares libres, embora com interface gráfica, tipo Orange. O que eu mais utilizei foi o que chama Nine, que na verdade é K9. Vou pegar ele aqui, o site.

56:20 - Gabriel Goes Rocha de Lima
Mas eu digo de texto generativo, de GPT. O que você pensa sobre?

56:26 - Marco Antonio Couto Junior
Eu acho que eu uso. Eu uso muito, já há alguns anos. Desde a época que eu estava trabalhando na Vale, isso me otimiza muito. Você utiliza alguma interface de desenvolvimento, tipo o VSCode, alguma coisa do tipo?

56:44 - Gabriel Goes Rocha de Lima
Eu uso o VSCode.

56:46 - Marco Antonio Couto Junior
Quando eu vou programar, eu uso o VSCode ou o outro lado. Ou o Jupyter Notebook. Eu abro o Jupyter Notebook no VSCode. Eu tenho feito muita coisa com o VSCode. Com notebooks, né? E aí, se for uma coisa que eu talvez precise integrar mais com ferramentas do Google e tal, aí eu vou no Colab mesmo. Ou para a Alva, né? Vocês viram lá, né? Eu fiz a matéria do Passat. Então, aí eu vou no Colab. Mas as coisas, assim, mais para projetos, eu fico bastante focado no VS Code, assim. E, cara, essas IAs generativas aí, assim, eu não desenvolvo nada disso, eu uso. Primeiramente, um usuário, mas ainda não tive eu como... Não deu tempo pra mim, assim, na vida, de eu parar e começar a tentar desenvolver em cima disso, mas... Eu acho fantástico, assim, eu assino... Você assina o GPT? O OpenAI?

57:51 - Gabriel Goes Rocha de Lima
Então, já que você assina essa ferramenta, eu recomendo... Você utilizar o... Deixa eu fechar essa aba aqui... O Codex, para quem assina, ele é de graça. Você tem um limite mensal, você tem um limite semanal de porcentagem de tokens que você pode usar e tem um limite de 5 horas. Cara, essa ferramenta é muito boa. Por exemplo, a gente pode usar esse code... O Codebase. Aí ele vai ler todo o meu repositório e vai criar um texto MD nesses specs aqui. Essa pasta specs, ele tem esses arquivos Gmd, que é uma informação de texto sobre o que é o nosso repositório. Por exemplo, aqui a gente tem o roadmap, aqui no roadmap, ele vai informar quais são os próximos passos que a gente pode seguir, a gente vai pedindo pra ele criar isso, né? Então ele vai lendo essas informações e vai usando ela como um guia, assim, do que fazer. Por exemplo, aqui tem o project, que ele informa quais são as informações, a visão do projeto, o que ele pretende resolver, por exemplo, qual é o Python que tá usando, então ele meio que tá integrado no terminal, assim, ele consegue escrever arquivos pra você, ele consegue executar comandos pra você, ele faz testes, então é bem interessante, assim, e você já que tem o VSCode, você consegue colocar o seu OpenAI no VSCode, que é o código, né, você instala o plugin do código e já pode começar a usar. Você só tem um limite mensal. Ele tá lendo todos os meus arquivos e tá verificando a minha codebase. Ele meu tá código meio faz. Ele que tá compreendendo lendo o cada que um o dos arquivos e compreendendo o que o código faz. É bem interessante. Eu acho massa.

1:00:07 - Marco Antonio Couto Junior
Muito bom. Ele serve como aquele...

1:00:10 - Gabriel Goes Rocha de Lima
é um paradigma de navegador motorista, né? Em que a gente é o navegador e ele é o motorista. Então, a gente só vai falando pra ele o que ele precisa fazer, ele vai dando alguns ajustes, algumas informações e vai executando, né? Sim. O chat EPT é o contrário, o motorista é o navegador, ele vai falando, ah, você tem que executar esse script, a gente copia o script dele, cola no terminal e executa.

1:00:46 - Marco Antonio Couto Junior
Aqui é o contrário. Legal. É bem interessante. Ele tem assinatura também, né?

1:00:51 - Gabriel Goes Rocha de Lima
Isso, é aquela assinatura mais básica, acho que é 10 dólares, 20 dólares. 20 dólares, 100 reais por mês, mais ou menos. É, eu uso a conta do meu pai. Ele paga e não usa o código que eu estou usando. E o modelo dele é melhor do que o do ChatGPT, é o 5.3 que tem aqui. O ChatGPT não tem acesso a esse modelo. Ah, legal.

1:01:18 - Marco Antonio Couto Junior
Legal, cara, eu vou olhar sim sim. Qual o terminal aí para o seu Linux? Porque eu vejo que você está com um terminal...

1:01:27 - Gabriel Goes Rocha de Lima
Então, eu estou usando... Essa ferramenta é NeoVim.

1:01:30 - Marco Antonio Couto Junior
Eu uso o Fulgrimo com o NeoVim. Eu usei menos Vim. Eu sou muito lindo ainda, mas eu quero cada vez mais. Durante o pós-doc eu usei muito. Já usei um pouco na vida. Esse daqui é o NeoVim.

1:01:49 - Gabriel Goes Rocha de Lima
É o Vim um pouco diferente. Ele é mais simples de programar porque ele é em lua. Configurar ele todo em lua. Aí ele fica mais personalizável, assim.

1:02:02 - Marco Antonio Couto Junior
Sim, legal. Legal isso aí. Eu vou olhar, então...

1:02:06 - Gabriel Goes Rocha de Lima
Dá uma olhada no Codex, instala ele no seu VSCode que você vai gostar bastante.

1:02:13 - Marco Antonio Couto Junior
Sim. Eu uso outras coisas também, né? Tipo assim, até ajuda a eu estudar pra aula, né? Tem o Sitespace, que eu assino também. Bem focado em pesquisa acadêmica, né? Então ele te ajuda a fazer revisão de literatura, ele monta... Mas é tipo um chat, um chat RPG, só com foco na academia, na pesquisa científica. Me ajuda a escrever projetos, porque ele acha artigos, que não são tão óbvios, é outra coisa que eu faço também. SciSpace, ajuda a preparar a aula, porque aí me ajuda a achar as referências e faz resumos, interage com o paper. Essa coisa é chamada SciSpace. Mas eu gostei do Codex.

1:03:11 - Gabriel Goes Rocha de Lima
Dá uma chance para o Codex. Ele tem essas skills aqui, que você consegue melhorar o funcionamento do Codex dando especialidades para ele. Então, aí eu estou usando essa TLC Spec Driven, que é do TechLeads, eu não sei se você conhece, é um grupo de programadores, tem o TechLeads, daí ele serve para você ler o seu repositório, fazer o design do repositório, criar tasks, executar as tasks, ele é bem interessante esse TLC Spec Driven. Vale a pena dar uma olhada, né? Pelo menos instalar o Codecs e depois você dá uma olhada nessas skills.

1:03:54 - Marco Antonio Couto Junior
É bem interessante. Vou olhar, sim. Vou olhar, vou tentar testar o Codecs.

1:04:00 - Gabriel Goes Rocha de Lima
Como que eu poderia tomar esse primeiro passo para poder utilizar o laboratório do... Ah, eu acho que...

1:04:08 - Unidentified Speaker
O computador que quem comprou foi a Camila, né? É bom dar um toque nela,
