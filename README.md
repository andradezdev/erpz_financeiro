# ERPZ Financeiro — Cobrança Bancária, Boletos Registrados, CNAB 240/400 e PIX Dinâmico

Solução corporativa de **Gestão Financeira e Cobrança Bancária Brasileira** desenvolvida nativamente para o **Frappe Framework** e **ERPNext** (v16), proporcionando automação completa do ciclo de Contas a Receber: emissão de boletos bancários com código de barras Febraban, PIX Cobrança dinâmico (Boleto Híbrido), geração de arquivos de Remessa CNAB 240/400 e processamento de arquivos de Retorno CNAB com baixa automática de faturas e conciliação bancária.

---

## Sumário Executivo

O **ERPZ Financeiro** integra a gestão de faturamento do ERPNext à rede bancária nacional sem necessidade de intermediários ou plataformas pagas de terceiros:
1. **Contas de Cobrança Bancária**: Parametrização flexível para os principais bancos brasileiros (Banco do Brasil, Itaú, Bradesco, Santander, Caixa Econômica, Sicoob, Sicredi, Banco Inter e Nubank).
2. **Boletos Bancários Registrados**: Emissão a partir das faturas de venda (`Sales Invoice`), com cálculo algorítmico do Código de Barras Febraban (44 posições), Linha Digitável (47 posições com DVs módulo 10 e 11) e Fator de Vencimento oficial.
3. **PIX Dinâmico e Boleto Híbrido**: Geração de QR Code PIX com Payload EMVCo oficial do Banco Central (Padrão BR Code com CRC16-CCITT), permitindo ao cliente pagar via código de barras tradicional ou por liquidação instantânea via PIX.
4. **Remessa CNAB (Envio ao Banco)**: Geração de arquivos posicionais `.REM` nos formatos **CNAB 240** e **CNAB 400** prontos para transmissão no Internet Banking ou EDI bancário.
5. **Retorno CNAB (Baixa Automática)**: Processamento de arquivos `.RET` devolvidos pelos bancos, identificando liquidações (código `06`), criando automaticamente o recebimento (`Payment Entry`) no ERPNext, baixando a fatura e registrando as despesas de tarifas bancárias.
6. **Impressão Oficial de Boletos em PDF**: Layout padronizado Febraban gerado em PDF com Recibo do Pagador, Ficha de Compensação e código de barras óptico.

---

## 1. Arquitetura e Modelo de Dados

| DocType | Tipo | Finalidade |
| :--- | :--- | :--- |
| **`Configuracao Conta Bancaria`** | Cadastro | Cadastro da conta corrente de cobrança: Banco (001, 341, 237, etc.), Agência, Conta, Carteira, Código do Beneficiário/Convênio, Padrão CNAB (240 ou 400), regras de juros/multa/protesto e Chave PIX. |
| **`Boleto Bancario`** | Principal | Registro do boleto emitido vinculado à fatura (`Sales Invoice`). Armazena Nosso Número, data de vencimento, valor, código de barras de 44 dígitos, linha digitável de 47 dígitos, QR Code PIX, dados do pagador e status (*Pendente, Remessa Gerada, Registrado, Liquidado, Baixado*). |
| **`Remessa CNAB`** | Operação | Lote de remessa enviado ao banco. Consolida os boletos a registrar, gera o sequencial da remessa e monta o arquivo posicional de texto (.REM). |
| **`Remessa CNAB Item`** | Tabela Filha | Linhas dos boletos incluídos no lote de remessa. |
| **`Retorno CNAB`** | Operação | Leitura e processamento do arquivo de retorno bancário (.RET). Identifica títulos liquidados, valores pagos e tarifas, executando a baixa automática. |
| **`Retorno CNAB Item`** | Tabela Filha | Detalhamento das ocorrências processadas no arquivo de retorno (liquidações, confirmações de entrada, baixas). |

---

## 2. Emissão de Boletos e Boleto Híbrido com PIX

```
Fatura de Venda (Sales Invoice)
   └── Geração do Boleto Bancário
         ├── Cálculo do Fator de Vencimento e DVs Módulo 10 e 11
         ├── Montagem do Código de Barras Febraban (44 dígitos) e Linha Digitável
         ├── Geração do Payload PIX BR Code com CRC16-CCITT (Boleto Híbrido)
         └── Emissão do PDF da Ficha de Compensação com Código de Barras + QR Code
```

* **Impressão em PDF**: Layout completo contendo os dados do Beneficiário, Pagador, Instruções de Caixa (Juros, Multa e Prazo de Protesto), Linha Digitável destacada, QR Code PIX e Código de Barras óptico.
* **Boleto Híbrido**: O cliente pode optar por pagar pelo código de barras ou efetuar a leitura do QR Code PIX no aplicativo do banco, garantindo liquidação imediata 24/7.

---

## 3. Fluxo de Remessa e Retorno CNAB

### 3.1 Geração de Remessa (`.REM`)
1. No menu **Remessas CNAB**, o usuário seleciona a Conta Bancária.
2. O sistema filtra os boletos com status **Pendente** emitidos para aquela conta.
3. Com 1 clique em **`Gerar Arquivo de Remessa`**:
   - Monta a estrutura posicional (Header de Arquivo, Header de Lote, Segmentos P, Q, R e Trailers para CNAB 240; ou Registros 0, 1 e 9 para CNAB 400).
   - Incrementa o sequencial da remessa.
   - Atualiza o status dos boletos para **Remessa Gerada**.
   - Disponibiliza o download imediato do arquivo `.REM` para transmissão bancária.

### 3.2 Leitura de Retorno (`.RET`) e Baixa Automática
1. No menu **Retornos CNAB**, o usuário anexa o arquivo `.RET` recebido do banco.
2. Com 1 clique em **`Processar Arquivo de Retorno`**:
   - O sistema lê linha a linha os registros de retorno.
   - Identifica os títulos pelo **Nosso Número**.
   - Para títulos liquidados (Ocorrência `06` ou `05`):
     - Atualiza o boleto para **Liquidado / Pago** com a data e valor real pago.
     - Localiza a `Sales Invoice` correspondente.
     - **Cria automaticamente o `Payment Entry`** (Recebimento) no ERPNext na conta bancária correta e baixa o Contas a Receber.
     - Registra o valor das tarifas bancárias cobradas.

---

## 4. Estrutura de Diretórios e Código-Fonte

```
erpz_financeiro/
├── desktop_icon/
│   └── erpz_financeiro.json       # Ícone oficial no Desk
├── erpz_financeiro/
│   ├── doctype/
│   │   ├── configuracao_conta_bancaria/ # Contas de cobrança e convênios
│   │   ├── boleto_bancario/       # Emissão e impressão de boletos
│   │   ├── remessa_cnab/          # Lotes de remessa bancária
│   │   ├── remessa_cnab_item/     # Títulos da remessa
│   │   ├── retorno_cnab/          # Processamento de retorno e baixa automática
│   │   └── retorno_cnab_item/     # Ocorrências do retorno
│   ├── workspace/
│   │   └── erpz_financeiro/       # Painel de controle financeiro
│   └── workspace_sidebar/
│       └── erpz_financeiro.json   # Menu lateral exclusivo de finanças
├── services/
│   ├── boleto.py                  # Cálculos matemáticos Febraban e PDF
│   ├── cnab240.py                 # Gerador e parser posicional CNAB 240
│   ├── cnab400.py                 # Gerador e parser posicional CNAB 400
│   └── pix.py                     # Gerador EMVCo BR Code e CRC16 do Banco Central
├── hooks.py
├── setup.py                       # Inicialização e vínculos
└── pyproject.toml
```

---

## Licença

Distribuído sob licença MIT. Desenvolvido para o ecossistema ERPZ / Frappe Framework v16.
