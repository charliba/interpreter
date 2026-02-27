# Schema do Banco de Dados — Joel

## Diagrama ER (Mermaid)

```mermaid
erDiagram
    User ||--o{ Document : "uploaded_by"
    User ||--o{ AnalysisRequest : "user"
    Document ||--o{ AnalysisRequest : "document"
    AnalysisRequest ||--o| Report : "analysis (1:1)"

    User {
        int id PK
        string username
        string email
        string password
        datetime date_joined
    }

    Document {
        uuid id PK
        file file
        string original_filename
        string file_type
        int file_size
        text extracted_text
        json extraction_metadata
        int uploaded_by FK
        datetime uploaded_at
    }

    AnalysisRequest {
        uuid id PK
        uuid document FK
        int user FK
        text user_objective
        string professional_area
        string professional_area_detail
        string geolocation
        string language
        boolean include_market_references
        string search_scope
        string report_type
        string status
        text error_message
        datetime created_at
        datetime updated_at
    }

    Report {
        uuid id PK
        uuid analysis FK "OneToOne"
        text content_html
        text content_markdown
        json references
        json search_results_raw
        text joel_reasoning
        file file_pdf
        file file_docx
        file file_xlsx
        file file_txt
        datetime created_at
    }
```

## Status Flow (AnalysisRequest)

```mermaid
stateDiagram-v2
    [*] --> pending : criado
    pending --> extracting : Docling inicia
    extracting --> analyzing : texto extraído
    analyzing --> searching : Joel analisando
    searching --> generating : referências obtidas
    generating --> completed : relatório salvo
    extracting --> error : falha parsing
    analyzing --> error : falha LLM
    searching --> error : falha busca
    generating --> error : falha geração
    error --> pending : retry
```

## Campos de Escolha

### professional_area
- `financeiro`, `juridico`, `saude`, `estetica`, `educacao`
- `tecnologia`, `treinamento`, `protocolo`, `marketing`
- `engenharia`, `outro`

### report_type
- `analitico` — Análise detalhada com métricas
- `comparativo` — Comparação com mercado/referências
- `resumo_executivo` — Síntese para decisores
- `tecnico` — Parecer técnico estruturado
- `parecer` — Opinião profissional fundamentada

### language
- `pt-BR` — Português (Brasil)
- `en` — English
- `es` — Español

### status
- `pending` → `extracting` → `analyzing` → `searching` → `generating` → `completed`
- Qualquer estado pode ir para `error`
