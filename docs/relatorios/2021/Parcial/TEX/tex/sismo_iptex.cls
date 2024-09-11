% Classe IPT Sismologia
%
% --------------------------------------------------------------------------------------
% Instituto de Pesquisas Tecnológicas
% Sessão de Obras Civis
% Setor de Sismologia
%
% Autor: Gabriel Góes Rocha de Lima
% Supervisor: Lucas Alexandre Schirbel
%
% Modelo originariamente baseado no modelo de Relatório Técnico criado para o túnel de
% vento pelo Pesquisador Paulo Jabardo. E adaptado de IPT Document Class.
%
% --------------------------------------------------------------------------------------
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{sismo_iptex}[2024/04/23 Classe Sismologia IPT]
\DeclareOption{10pt}{\def\@@ptsize{10pt}}
\DeclareOption{11pt}{\def\@@ptsize{11pt}}
\DeclareOption{12pt}{\def\@@ptsize{12pt}}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax
\LoadClass[a4paper, oneside, onecolumn, final,\@@ptsize]{article}

% Incluindo pacotes
\RequirePackage{mdframed}
\RequirePackage[hidelinks]{hyperref}
\RequirePackage[utf8]{inputenc}
\RequirePackage[T1]{fontenc}
\RequirePackage{mathtools}
\RequirePackage{amsmath}
\RequirePackage{amsthm}
\RequirePackage{amsbsy}
\RequirePackage{amsfonts}
\RequirePackage{amssymb}
\RequirePackage{latexsym}
\RequirePackage{mathabx}
\RequirePackage{graphicx}
\RequirePackage[scaled]{helvet} % Mudar de "helvet" para "uarial" caso fonte arial esteja instalada
\RequirePackage{url}
\RequirePackage{fancyhdr}
\RequirePackage{indentfirst}
\RequirePackage{color}
\RequirePackage{float}
\RequirePackage{multirow}
\RequirePackage{lscape}
\RequirePackage{lastpage}
\RequirePackage[margin=15pt, font=small, labelfont=bf, labelsep=endash, centerlast]{caption}
\RequirePackage{subfig}
\RequirePackage[final]{pdfpages}
\RequirePackage{setspace}
\RequirePackage{changepage}
\RequirePackage[titles, subfigure]{tocloft}
\RequirePackage{ifthen}
\RequirePackage{lipsum} % Apenas para gerar Lorem Ipsum dummy text
\RequirePackage{sectsty}
\RequirePackage{textcomp}
\RequirePackage{booktabs}
\RequirePackage{stmaryrd}
\RequirePackage{siunitx}
\RequirePackage{upgreek} % Para letras gregas não itálicas no texto
\RequirePackage[table]{xcolor}
\RequirePackage{tabularx}
\RequirePackage{enumitem}
\RequirePackage{geometry}
\RequirePackage{capt-of}
\RequirePackage{xargs}
% Tabelas longas
\RequirePackage{longtable}
\RequirePackage{makecell}
\RequirePackage{adjustbox}
% Página no modo paisagem
\RequirePackage{pdflscape}
\RequirePackage[a-1b]{pdfx}
\RequirePackage{array}
	\setlist{nolistsep}
	\definecolor{green}{HTML}{66FF66}
	\definecolor{myGreen}{HTML}{009900}
	\newcolumntype{L}[1]{>{\raggedright\let\newline\\\arraybackslash\hspace{0pt}}m{#1}}
	\newcolumntype{C}[1]{>{\centering\let\newline\\\arraybackslash\hspace{0pt}}m{#1}}
	\newcolumntype{R}[1]{>{\raggedleft\let\newline\\\arraybackslash\hspace{0pt}}m{#1}}
	\renewcommand{\familydefault}{\sfdefault}
	\renewcommand{\arraystretch}{1.5}
% Tamanhos de fonte das seções e subseções e alterações no TOC
\sectionfont{\bfseries\large\MakeUppercase}
\renewcommand{\cftsecfont}{\bfseries}
\renewcommand{\cftsecpagefont}{\bfseries}
\subsectionfont{\bfseries\large}
\renewcommand{\cftsubsecfont}{\bfseries}
\renewcommand{\cftsubsecpagefont}{\bfseries}
\subsubsectionfont{\bfseries\normalsize}
\renewcommand{\cftsubsubsecfont}{\bfseries\normalsize}
\renewcommand{\cftsubsubsecpagefont}{\bfseries}
\setcounter{tocdepth}{4}
\setcounter{secnumdepth}{4}
\paragraphfont{\normalsize\normalfont}
\renewcommand\@pnumwidth{3.2em}
\renewcommand{\cftsecleader}{\cftdotfill{\cftdotsep}}
% Comandos
	\renewcommand{\familydefault}{\sfdefault}
	\renewcommand{\headrulewidth}{0pt}
	\renewcommand{\topfraction}{1}
	\renewcommand{\bottomfraction}{1}
	\renewcommand{\textfraction}{0}
	\renewcommand{\floatpagefraction}{0.8}
	\newcommand{\n}[1]{$\text{#1}$}
	\newcommand{\docNum}[1]{\gdef\inserirDocNum{#1}}
	\newcommand{\cancelaDoc}[1]{\gdef\inserirCancelaDoc{#1}}
	\newcommand{\cliente}[6]{
        \gdef\inserirNomeCliente{#1}
        \gdef\inserirSiglaCliente{#2}
		\gdef\inserirLocalCliente{#3}
        \gdef\inserirCEPCliente{#4}
		\gdef\inserirCidadeCliente{#5}
        \gdef\inserirEstadoCliente{#6}
    }
	\newcommand{\interessado}[5]{
        \gdef\inserirNomeInt{#1}
		\gdef\inserirLocalInt{#2}
        \gdef\inserirCEPInt{#3}
		\gdef\inserirCidadeInt{#4}
        \gdef\inserirEstadoInt{#5}
    }
	\newcommand{\equip}[1]{\gdef\inserirEquip{#1}}
	\newcommand{\referencia}[1]{\gdef\inserirReferencia{#1}}
	\newcommand{\data}[1]{\gdef\inserirData{#1}}
	\newcommand{\titulo}[1]{\gdef\inserirTitulo{#1}}
	\newcommand{\tipo}[1]{\gdef\inserirTipo{#1}}
	\newcommand{\unidade}[2]{
        \gdef\inserirUnidade{#1}
        \gdef\inserirUnidadeSigla{#2}
    }
	\newcommand{\lab}[1]{\gdef\inserirLab{#1}}
	\newcommand{\cabecalhoAcred}[1]{\gdef\inserirCabecalhoAcred{#1}}
	\newcommand{\selo}[1]{\gdef\inserirSelo{#1}}
	\newcommand{\parConfig}[1]{#1}
	\newcommand{\dummylabel}[2]{
        \def\@currentlabel{#2}
        \label{#1}
    }
    \newcommand{\periodo}[2]{
        \gdef\inserirInicio{#1}
        \gdef\inserirFim{#2}
    }
	\newcommand\firstup[1]{\firstupaux#1\relax}
	\def\firstupaux#1#2\relax{
        \MakeUppercase{#1}
        \MakeLowercase{#2}
    }
% Parágrafo
	\setlength{\voffset}{-25.4mm}
	\setlength{\oddsidemargin}{-3.5mm}
	\setlength{\topmargin}{5mm}
	\setlength{\headheight}{28mm}
	\setlength{\headsep}{5mm}
	\setlength{\marginparsep}{0mm}
	\setlength{\textheight}{230mm}
	\setlength{\textwidth}{170mm}
	\setlength{\footskip}{25mm}
	\setlength{\marginparwidth}{0mm}
	\def\mypagestyle#1{\csname myps#1\endcsname}
	\newcommand{\mypsCC}{
		\setlength{\voffset}{-25.4mm}
		\setlength{\oddsidemargin}{-3.5mm}
		\setlength{\topmargin}{5mm}
		\setlength{\headheight}{42mm}
		\setlength{\headsep}{5mm}
		\setlength{\marginparsep}{0mm}
		\setlength{\textheight}{215mm}
		\setlength{\textwidth}{170mm}
		\setlength{\footskip}{25mm}
		\setlength{\marginparwidth}{0mm}
	}
	\linespread{1.3} % espaçamento de 1,5 parecido com Word
	\setcounter{topnumber}{5}
	\setcounter{bottomnumber}{5}
	\setcounter{totalnumber}{10}
	\setlength{\floatsep}{15pt}
	\setlength{\textfloatsep}{20pt}
	\setlength{\parskip}{6pt}
	\setlength{\parindent}{1.25cm}

% Cabeçalhos e rodapé
	\lhead{\includegraphics[scale=0.9]{tex/figuras_tex/headImage.pdf}}
	\chead{}
    \rhead{{\footnotesize \thepage}}
	\lfoot{}
	\cfoot{}
	\rfoot{\includegraphics[scale=1.0]{tex/figuras_tex/footImage.pdf}}
	\pagestyle{fancy}
	\fancypagestyle{geral}{
    		\rhead{{\footnotesize \thepage /\pageref{LastPage}}}
	}

	\fancypagestyle{timbrado}{
        \rhead{}   
    }
    \fancypagestyle{tipo_pre}{\rhead{\footnotesize \inserirTipo~n\textordmasculine~\inserirDocNum~-~\thepage}}
    \fancypagestyle{tipo_doc}{\rhead{{\footnotesize \inserirTipo~n\textordmasculine~\inserirDocNum~-~\thepage /\pageref{LastPage}}}}
	\fancypagestyle{calibr_pag1}{
		\lhead{\renewcommand{\arraystretch}{1.0}
			\noindent\begin{tabular}{@{}l}
			\includegraphics[scale=0.9]{tex/figuras_tex/headImage.pdf}\\
			\footnotesize\textbf{\inserirLab/\inserirUnidade}\\
			\footnotesize\textbf{}
			\end{tabular}
		}
		\rhead{
            \renewcommand{\arraystretch}{1.3}
			\noindent\begin{tabular}{@{}r}\\
			\thepage /\pageref{LastPage} \\
			\small\textbf{}
			\end{tabular}
		}
		\rfoot{
            \includegraphics[scale=1.2]{tex/figuras_tex/footImage.pdf}}
	}
	\fancypagestyle{calibr_doc}{
		\lhead{
            \renewcommand{\arraystretch}{1.0}
		    \noindent\begin{tabular}{@{}l}
			\includegraphics[scale=0.9]{tex/figuras_tex/headImage.pdf}\\
			\footnotesize\textbf{\inserirLab/\inserirUnidade} \\
			\ifdefined
                \inserirCabecalhoAcred
                \footnotesize\textbf{\inserirCabecalhoAcred}\\
			\else\\
				\fi
			\end{tabular}
		}
		\rhead{
            \renewcommand{\arraystretch}{1.3}
			\noindent\begin{tabular}{@{}r} \\
			\thepage /\pageref{LastPage} \\
			\footnotesize\textbf{\inserirTipo~n\textordmasculine~\inserirDocNum}
            \end{tabular}
		}
		\rfoot{
            \includegraphics[scale=1.2]{tex/figuras_tex/footImage.pdf}}
	}

% Capa
	\newcommand{\capa}{
	\thispagestyle{timbrado}
	\begin{adjustwidth*}{1.5cm}{1.5cm}
		{\setstretch{1.0}
			\begin{flushright}
				\textbf{\large\MakeUppercase{\inserirTipo}}\\
				\ifdefined\inserirDocNum
					\textbf{\large\inserirDocNum}\\
				\fi

				\ifdefined\inserirSiglaCliente
					\inserirSiglaCliente\\
				\fi

				\inserirData \\
				\vspace{3cm}
				\inserirTitulo \\

				\ifdefined\inserirNomeCliente
					\vspace{3cm}
					\textbf{CLIENTE} \\
					\inserirNomeCliente \\
				\fi

				\vspace{3cm}

				\ifdefined\inserirUnidade
					\textbf{UNIDADE RESPONSÁVEL} \\
					\inserirUnidade ~-- \inserirUnidadeSigla \\
				\fi

				\ifdefined\inserirLab
					\inserirLab \\
				\fi

				\vspace{3cm}

                \ifdefined\periodo
                    \textbf{PERÍODO DE ANÁLISE} \\
                    \textbf{Início: }\inserirInicio \\
                    \textbf{Fim: }\inserirFim \\
                \fi

			\end{flushright}
		}
	\end{adjustwidth*}
	\clearpage
}

% Resumo
	\newcommand{\resumo}[3][\textbf{Palavras-chave:}]{
		\setcounter{page}{1}
		\renewcommand{\thepage}{\roman{page}}
		\section*{RESUMO}
		#2
		\vspace{0.5cm}
		#1 #3
		\pagebreak
	}

% Abstract
    \newcommand{\resumoeng}[3][\textbf{Keywords:}]{
        \setcounter{page}{1}
        \renewcommand{\thepage}{\roman{page}}
        \section*{ABSTRACT}
        #2
        \vspace{0.5cm}
        #1 #3
        \pagebreak
    }

% Página com dados do cliente e título para documentos em geral
	\newcommand{\idCliente}{
		\begin{center}
		{\setstretch{0.5}
			\begin{tabular}{c}
				{\large \textbf{\MakeUppercase{\inserirTipo}~N\textordmasculine~\inserirDocNum}} \\
				\ifdefined\inserirCancelaDoc
					Cancela e substitui o~\inserirCancelaDoc
				\fi
			\end{tabular}
		}
		\end{center}
		\vspace{0.2cm}

		{\setstretch{0.5}
		\noindent\begin{tabular}{lp{0.75\textwidth}}
		\ifdefined\inserirTitulo
			\textbf{Título:} & \textbf{\inserirTitulo} \\
			& \\
		\fi
		\textbf{Cliente:} & \textbf{\inserirNomeCliente} \\
			& \textbf{\inserirLocalCliente} \\
			& \textbf{CEP \inserirCEPCliente ~-- \inserirCidadeCliente ~-- \inserirEstadoCliente} \\
		\ifdefined\inserirNomeInt
		& \\
		\textbf{Interessado:} & \textbf{\inserirNomeInt} \\
			& \textbf{\inserirLocalInt} \\
			& \textbf{\inserirCEPInt ~-- \inserirCidadeInt ~-- \inserirEstadoInt} \\
		\fi
		\ifdefined\inserirEquip
		& \\
		\textbf{Item:} & \textbf{\inserirEquip} \\
		\fi
		\ifdefined\inserirReferencia
		& \\
		\textbf{Referência:} & \textbf{\inserirReferencia} \\
		\fi
		\end{tabular}
		}
	}

% Página com dados do cliente para certificado acreditado
	\newcommand{\idClienteAcred}{
		\begin{center}
		{\setstretch{0.5}
			\begin{tabular}{c}
				{\large \textbf{\MakeUppercase{\inserirTipo}~N\textordmasculine~\inserirDocNum}} \\
				\ifdefined\inserirCancelaDoc
				Cancela e substitui o~\inserirCancelaDoc
				\fi
			\end{tabular}
		}
		\end{center}
		\ifdefined\inserirEquip
			\vspace{0.2cm}
		\fi

		\ifdefined\inserirNomeInt
			\vspace{-1cm}
		\else
			\vspace{-2cm}
		\fi

		{\setstretch{0.5}
		\noindent\begin{tabular}{lp{0.6\textwidth}}
		\textbf{Cliente:} & \textbf{\inserirNomeCliente}\\
			& \textbf{\inserirLocalCliente} \\
			& \textbf{\inserirCEPCliente ~-- \inserirCidadeCliente ~-- \inserirEstadoCliente}\\
		\ifdefined\inserirNomeInt
		& \\
		\textbf{Interessado:} & \textbf{\inserirNomeInt}\\
			& \textbf{\inserirLocalInt} \\
			& \textbf{\inserirCEPInt ~-- \inserirCidadeInt ~-- \inserirEstadoInt}\\
		\fi
		\ifdefined\inserirEquip
		& \\
		\textbf{Item:} & \textbf{\inserirEquip} \\
		\fi
		\ifdefined\inserirReferencia
		& \\
		\textbf{Referência:} & \textbf{\inserirReferencia}\\
		\fi
		\end{tabular}}  \hfill  \ifdefined\selo \includegraphics[height=0.15\textheight]{\inserirSelo} \fi
	}

	\newcommand{\inserirFigura}[6][htb!]{
		\begin{figure}[#1]
			\centering
			\captionsetup{justification=raggedright,
				singlelinecheck=false
			}
			\captionsetup{#3}
			\caption{#4}
			\includegraphics[#3]{tex/figuras_tex/#2}
			\caption*{#5}
			#6
		\end{figure}
	}

% Tabelas
% Função de repetição
\makeatletter
\newcount\my@repeat@count
\newcommand{\myrepeat}[2]{%
	\begingroup
	\my@repeat@count=\z@
	\@whilenum\my@repeat@count<#1\do{#2\advance\my@repeat@count\@ne}%
	\endgroup
}
\makeatother

	\newcommandx{\inserirTabela}[8][1=H, 2=\normalsize]{
		\begin{table}[#1]
			#2
			\centering
			\begin{minipage}{#4} \centering
				\captionsetup{justification=raggedright,
					singlelinecheck=false
				}
				\caption{#6}
				\begin{tabular}{#3}
					#5
				\end{tabular}
				\caption*{#7}
				#8
			\end{minipage}
		\end{table}

}
	\newcommand{\inserirTabelaLonga}[7]{
        \begin{small}
		\begin{center}
        \begin{landscape}
			\begin{longtable}{#1}
				\captionsetup{justification=raggedright,
					singlelinecheck=false
				}
				\multicolumn{#2}{l}{\parbox{\LTcapwidth}{\small\singlespacing\textbf{Tabela \thetable} -- #6}}
				\vspace{0.3cm} \\
				\hline
				#3 \\
				\hline
				\endhead
				\hline
				\multicolumn{#2}{l}{\small\textit{Continua na próxima página}} \\
				\endfoot
				\hline
				\multicolumn{#2}{l}{\parbox{\LTcapwidth}{\small\singlespacing#7}}
				\endlastfoot
				#5
			\end{longtable}
        \end{landscape}
        \end{center}
        \end{small}
	}

% Página com assinaturas
    \newcommand{\assinaturaLucas}{
        \begin{table}[b]
        \begin{adjustwidth}{0pt}{-9cm} % Ajusta a margem direita em -3cm
        \centering
        \setlength{\arrayrulewidth}{0.9pt} % Espessura das linhas verticais
        \begin{tabular}{|c|}
            \hline
            Cidades, Infraestrutura e Meio Ambiente \\
            \hline
            Seção de Obras Civis \\
            \hline \\[1.0pt]
            \includegraphics{tex/figuras_tex/assinatura.png} \\[5.0pt]
            \hline \\[-25.0pt]
            Físico Me. Lucas Alexandre Schirbel \\[-7.0pt]
            Pesquisador \\[-7.0pt]
            RE: 117113 \\[0.0pt]
            \hline
        \end{tabular}
        \end{adjustwidth}
        \end{table}
}                

%% Três assinaturas digitais
	\newcommand{\assinaturaTresDigital}[6]{
		\begin{flushright}
		\textbf{São Paulo, \inserirData.}
		% Assinaturas
			{\scriptsize\singlespacing
			\begin{tabular}{p{8cm}p{8cm}}
				\begin{center} \textbf{#1} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#2} \end{center} &
				\begin{center} \textbf{#3} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#4} \end{center} \\
				& \begin{center} \textbf{#5} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#6} \end{center}\\ \\
			\end{tabular}
			}
		\end{flushright}
		\begin{center}
			\includegraphics[scale=1]{tex/figuras_tex/digital.png}
		\end{center}
		\pagebreak
	}

%% Três assinaturas sem identificação de ass. digital
	\newcommand{\assinaturaTres}[6]{
	\begin{flushright}
		\textbf{São Paulo, \inserirData.}
	% Assinaturas
		{\scriptsize\singlespacing
			\begin{tabular}{p{8cm}p{8cm}}
				\begin{center} \textbf{#1} \\ \vspace{1.2cm} \textbf{#2} \end{center} &
				\begin{center} \textbf{#3} \\ \vspace{1.2cm} \textbf{#4} \end{center} \\
				& \begin{center} \textbf{#5} \\ \vspace{1.2cm} \textbf{#6} \end{center}\\ \\
			\end{tabular}
		}
	\end{flushright}
	\pagebreak
}

%% Três assinaturas digitais - especial p/ certificado acreditado
	\newcommand{\assinaturaTresAcred}[6]{
		\begin{flushright}
			\textbf{São Paulo, \inserirData.}
		% Assinaturas
			{\scriptsize\singlespacing
			\begin{tabular}{p{8cm}p{8cm}}
				\begin{center} \textbf{#1} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#2} \end{center} &
				\begin{center} \textbf{#3} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#4} \end{center} \\
				\begin{center} \textbf{#5} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#6} \end{center}\\ \\
			\end{tabular}
			}
		\end{flushright}
		\begin{center}
			\includegraphics[scale=1]{tex/figuras_tex/digital.png}
		\end{center}
		\noindent\textbf{“Este certificado atende aos requisitos de acreditação pela Cgcre, que avaliou a competência do laboratório e 		comprovou sua rastreabilidade a padrões nacionais de medida (ou ao Sistema Internacional de Unidades – SI).”}
		\pagebreak
	}

%% Duas assinaturas digitais Relatório Técnico
    \newcommand{\assinaturaDoisDigitalRelatorio}{
        \begin{flushright}
            \textbf{São Paulo, \inserirData.}
            % Assinaturas
            {\scriptsize\singlespacing
                \begin{tabular}{p{8cm}p{8cm}}
                    \hline
                    \begin{center} \textbf{CIDADES, INFRAESTRUTURA E MEIO AMBIENTE} \\ \vspace{0.1cm}
                        \textbf{Seção de Obras Civis} \\ \vspace{0.1cm}
                        \textbf{Engº Civil Diego Lapolli Bressan} \\ \vspace{0.1cm}
                        \textbf{Gerente Técnico} \\ \vspace{0.1cm}
                        \textbf{CREA 170028342-1 – RE 08733} \\ \vspace{0.1cm}
                        {\color{blue} Assinado Digitalmente} \\ \vspace{0.1cm}
                    \end{center} &

                    \begin{center} \textbf{CIDADES, INFRAESTRUTURA E MEIO AMBIENTE} \\ \vspace{0.1cm}
                        \textbf{Seção de Obras Civis} \\ \vspace{0.1cm}
                        \textbf{Geól. Me. Fabrício Araujo Mirandola} \\ \vspace{0.1cm}
                        \textbf{Diretor Técnico} \\ \vspace{0.1cm}
                        \textbf{CREASP Nº 5062055808 – RE 8658} \\ \vspace{0.1cm}
                        {\color{blue} Assinado Digitalmente}\\ \vspace{0.1cm} 
                    \end{center}
                \end{tabular}
            }
        \end{flushright}
        \begin{center}
            \includegraphics[scale=1]{tex/figuras_tex/digital.png}
        \end{center}
        \pagebreak
    }

%% Duas assinaturas digitais
	\newcommand{\assinaturaDoisDigital}[4]{
		\begin{flushright}
			\textbf{São Paulo, \inserirData.}
		% Assinaturas
			{\scriptsize\singlespacing
			\begin{tabular}{p{8cm}p{8cm}}
				\begin{center} \textbf{#1} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#2} \end{center} &
				\begin{center} \textbf{#3} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#4} \end{center}\\ \\
			\end{tabular}
			}
		\end{flushright}
		\begin{center}
			\includegraphics[scale=1]{tex/figuras_tex/digital.png}
		\end{center}
		\pagebreak
	}

%% Duas assinaturas sem identificação de ass. digital
	\newcommand{\assinaturaDois}[4]{
	\begin{flushright}
		\textbf{São Paulo, \inserirData.}
	% Assinaturas
		{\scriptsize\singlespacing
			\begin{tabular}{p{8cm}p{8cm}}
				\begin{center} \textbf{#1} \\ \vspace{0.8cm} \textbf{#2} \end{center} &
				\begin{center} \textbf{#3} \\ \vspace{0.8cm} \textbf{#4} \end{center}\\ \\
			\end{tabular}
		}
	\end{flushright}
	\pagebreak
}

%% Duas assinaturas digitais - especial p/ certificado acreditado
	\newcommand{\assinaturaDoisAcred}[4]{
		\begin{flushright}
			\textbf{São Paulo, \inserirData.}
		% Assinaturas
			{\scriptsize\singlespacing
			\begin{tabular}{p{8cm}p{8cm}}
				\begin{center} \textbf{#1} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#2} \end{center} &
				\begin{center} \textbf{#3} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\\textbf{#4} \end{center}\\ \\
			\end{tabular}
			}
		\end{flushright}
		\begin{center}
			\includegraphics[scale=1]{tex/figuras_tex/digital.png}
		\end{center}
		\noindent\textbf{“Este certificado atende aos requisitos de acreditação pela Cgcre, que avaliou a competência do laboratório e 		comprovou sua rastreabilidade a padrões nacionais de medida (ou ao Sistema Internacional de Unidades – SI).”}
		\pagebreak
	}

%% Uma assinatura digital
	\newcommand{\assinaturaUmDigital}[2]{
		\begin{flushright}
			\textbf{São Paulo, \inserirData.}
		% Assinaturas
			{\scriptsize\singlespacing
				\begin{tabular}{p{8cm}}
					\begin{center} \textbf{#1} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#2} \end{center} \\
				\end{tabular}
			}
		\end{flushright}
		\begin{center}
			\includegraphics[scale=1]{tex/figuras_tex/digital.png}
		\end{center}
		\pagebreak
	}

%% Uma assinatura sem identificação de ass. digital
\newcommand{\assinaturaUm}[2]{
	\begin{flushright}
		\textbf{São Paulo, \inserirData.}
	% Assinaturas
		{\scriptsize\singlespacing
			\begin{tabular}{p{8cm}}
				\begin{center} \textbf{#1} \\ \vspace{0.8cm} \textbf{#2} \end{center} \\
			\end{tabular}
		}
	\end{flushright}
	\pagebreak
}

%% Uma assinatura - especial p/ certificado acreditado
	\newcommand{\assinaturaUmAcred}[2]{
		\begin{flushright}
			\textbf{São Paulo, \inserirData.}
		% Assinaturas
			{\scriptsize\singlespacing
				\begin{tabular}{p{8cm}}
					\begin{center} \textbf{#1} \\ \vspace{0.2cm} {\color{blue} Assinado Digitalmente} \vspace{0.2cm} \\ \textbf{#2} \end{center} \\
				\end{tabular}
			}
		\end{flushright}
		\begin{center}
			\includegraphics[scale=1]{tex/figuras_tex/digital.png}
		\end{center}
		\noindent\textbf{“Este certificado atende aos requisitos de acreditação pela Cgcre, que avaliou a competência do laboratório e 		comprovou sua rastreabilidade a padrões nacionais de medida (ou ao Sistema Internacional de Unidades – SI).”}
		\pagebreak
	}

%% Bibliografia
	\newcommand{\bibliografia}[1]{
		\renewcommand{\refname}{Bibliografia}
		\addcontentsline{toc}{section}{Referências}
		\bibliography{#1}
	}

% Apêndices
% Apêndice de Relatório Técnico
\newcommand{\apendice}[4]{

	\dummylabel{#3}{#1}

	\addcontentsline{toc}{section}{APÊNDICE #1 - #2}
	\section*{APÊNDICE #1 - \MakeUppercase{#2}}

	\renewcommand{\thefigure}{#1.\arabic{figure}}
	\renewcommand{\thetable}{#1.\arabic{table}}
	\setcounter{figure}{0}
	\setcounter{table}{0}
}

% Anexos
% Anexo de Relatório Técnico, com folha de rosto
	\newcommand{\anexo}[4]{
	\dummylabel{#3}{#1}
	\fancypagestyle{anexo}{
		\rhead{{\footnotesize Anexo #1 do \inserirTipo~n\textordmasculine~\inserirDocNum~-~\thepage /\pageref{LastPage}}}
	}
	\pagestyle{anexo}
	\vspace*{5cm}
	\begin{center}
		\cftaddtitleline{toc}{section}{ANEXO #1 - #2}{#4 pág.}
		\large\textbf{ANEXO #1}
		\vspace{4cm}
		\large\bfseries\MakeUppercase{#2}
	\end{center}
	\pagebreak
	}

% Anexo de Certificado de Calibração, sem folha de rosto
	\newcommand{\anexoSemFolhaRosto}[3]{
	\dummylabel{#3}{#1}
	\fancypagestyle{anexo_sfr}{
		\lhead{\renewcommand{\arraystretch}{1.0}
				\noindent\begin{tabular}{@{}l}
				\includegraphics[scale=0.9]{tex/figuras_tex/headImage.pdf}\\
				\footnotesize\textbf{\inserirLab/\inserirUnidade} \\
				\ifdefined\inserirCabecalhoAcred
					\footnotesize\textbf{\inserirCabecalhoAcred}\\
				\else
					\\
				\fi
			\end{tabular}
		}
		\rhead{\renewcommand{\arraystretch}{1.3}
				\noindent\begin{tabular}{@{}r}
				\\
				\thepage /\pageref{LastPage} \\
			 	\footnotesize \textbf{Anexo #1 do~\footnotesize\inserirTipo~n\textordmasculine~\inserirDocNum}
			\end{tabular}
		}
		\rfoot{\includegraphics[scale=1.2]{tex/figuras_tex/footImage.pdf}}
	}
	\pagestyle{anexo_sfr}
	\begin{center}
		{\large \textbf{ANEXO #1 - #2}}
	\end{center}
	\renewcommand{\thefigure}{#1.\arabic{figure}}
	\renewcommand{\thetable}{#1.\arabic{table}}
	\setcounter{figure}{0}
	\setcounter{table}{0}
	}
