"""
Models for Interpretador de Documentos — Joel Agent

Four main models:
- Document: uploaded file + extracted text
- AnalysisRequest: user configuration for the analysis
- Report: generated professional report in multiple formats
- Suggestion: user suggestions/feedback for platform improvements
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Document(models.Model):
    """Documento enviado pelo usuário para análise."""

    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    original_filename = models.CharField(max_length=512)
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.PositiveIntegerField(default=0, help_text="Tamanho em bytes")
    extracted_text = models.TextField(
        blank=True, help_text="Texto extraído pelo Docling"
    )
    extraction_metadata = models.JSONField(
        default=dict, blank=True, help_text="Metadados da extração (páginas, tabelas, etc.)"
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="documents"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def __str__(self):
        return f"{self.original_filename} ({self.file_type})"

    @property
    def file_size_display(self):
        """Retorna tamanho formatado (KB, MB)."""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


class AnalysisRequest(models.Model):
    """Configuração da análise solicitada pelo usuário."""

    # === Choices ===
    class ProfessionalArea(models.TextChoices):
        FINANCEIRO = "financeiro", "Financeiro"
        JURIDICO = "juridico", "Jurídico"
        SAUDE = "saude", "Saúde"
        ESTETICA = "estetica", "Estética"
        EDUCACAO = "educacao", "Educação"
        TECNOLOGIA = "tecnologia", "Tecnologia"
        TREINAMENTO = "treinamento", "Treinamento"
        PROTOCOLO = "protocolo", "Protocolo"
        MARKETING = "marketing", "Marketing"
        ENGENHARIA = "engenharia", "Engenharia"
        OUTRO = "outro", "Outro"

    class ReportType(models.TextChoices):
        ANALITICO = "analitico", "Analítico"
        COMPARATIVO = "comparativo", "Comparativo"
        RESUMO_EXECUTIVO = "resumo_executivo", "Resumo Executivo"
        TECNICO = "tecnico", "Técnico"
        PARECER = "parecer", "Parecer"

    class Language(models.TextChoices):
        PT_BR = "pt-BR", "Português (Brasil)"
        EN = "en", "English"
        ES = "es", "Español"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        EXTRACTING = "extracting", "Processando documento..."
        ANALYZING = "analyzing", "Analisando conteúdo..."
        SEARCHING = "searching", "Pesquisando referências..."
        GENERATING = "generating", "Gerando relatório..."
        COMPLETED = "completed", "Concluído"
        CANCELLED = "cancelled", "Cancelado"
        ERROR = "error", "Erro"

    # === Fields ===
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="analyses"
    )
    user_objective = models.TextField(
        help_text="Descreva o que você quer analisar neste documento"
    )
    professional_area = models.CharField(
        max_length=50,
        choices=ProfessionalArea.choices,
        default=ProfessionalArea.OUTRO,
    )
    professional_area_detail = models.CharField(
        max_length=200,
        blank=True,
        help_text="Detalhe a área profissional com suas palavras",
    )
    geolocation = models.CharField(
        max_length=200,
        blank=True,
        help_text="País/região para busca de referências (ex: Brasil, São Paulo)",
    )
    language = models.CharField(
        max_length=10,
        choices=Language.choices,
        default=Language.PT_BR,
    )
    include_market_references = models.BooleanField(
        default=True,
        help_text="Incluir referências de mercado no relatório",
    )
    search_scope = models.TextField(
        blank=True,
        help_text="Palavras-chave adicionais para direcionar a busca na internet",
    )
    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
        default=ReportType.ANALITICO,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    processing_log = models.TextField(
        blank=True,
        help_text="Log progressivo do processamento (debug, visível apenas em localhost)",
    )
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="Quando o processamento iniciou"
    )
    requested_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="analysis_requests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Solicitação de Análise"
        verbose_name_plural = "Solicitações de Análise"

    def __str__(self):
        return f"Análise #{self.pk} — {self.document.original_filename} ({self.get_status_display()})"

    def append_log(self, message: str):
        """Adiciona mensagem timestamped ao log de processamento."""
        timestamp = timezone.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        self.processing_log = (self.processing_log or "") + line
        self.save(update_fields=["processing_log"])

    @property
    def elapsed_seconds(self) -> int | None:
        """Segundos desde o início do processamento."""
        if not self.started_at:
            return None
        end = self.completed_at or timezone.now()
        return int((end - self.started_at).total_seconds())

    def mark_started(self):
        self.started_at = timezone.now()
        self.processing_log = ""
        self.save(update_fields=["started_at", "processing_log"])
        self.append_log("Processamento iniciado")

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])
        self.append_log("Concluído com sucesso!")

    def mark_error(self, message):
        self.status = self.Status.ERROR
        self.error_message = message
        self.save(update_fields=["status", "error_message"])
        self.append_log(f"ERRO: {message}")


class Report(models.Model):
    """Relatório profissional gerado pelo Joel."""

    analysis = models.OneToOneField(
        AnalysisRequest, on_delete=models.CASCADE, related_name="report"
    )
    content_html = models.TextField(
        blank=True, help_text="Relatório completo em HTML (exibição na tela)"
    )
    content_markdown = models.TextField(
        blank=True, help_text="Relatório completo em Markdown"
    )
    references = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de referências encontradas [{title, url, snippet}]",
    )
    search_results_raw = models.JSONField(
        default=list,
        blank=True,
        help_text="Resultados brutos da pesquisa Tavily",
    )
    joel_reasoning = models.TextField(
        blank=True,
        help_text="Raciocínio do Joel sobre como construiu o relatório",
    )
    file_pdf = models.FileField(upload_to="reports/pdf/", blank=True)
    file_docx = models.FileField(upload_to="reports/docx/", blank=True)
    file_xlsx = models.FileField(upload_to="reports/xlsx/", blank=True)
    file_txt = models.FileField(upload_to="reports/txt/", blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        verbose_name = "Relatório"
        verbose_name_plural = "Relatórios"

    def __str__(self):
        return f"Relatório #{self.pk} — {self.analysis.document.original_filename}"


class Suggestion(models.Model):
    """Sugestão de melhoria enviada por usuários da plataforma."""

    class Category(models.TextChoices):
        FEATURE = "feature", "Nova Funcionalidade"
        UX = "ux", "Melhoria de UX"
        INTEGRATION = "integration", "Integração"
        REPORT = "report", "Relatórios"
        BUG = "bug", "Correção de Bug"
        OTHER = "other", "Outro"

    class Priority(models.TextChoices):
        LOW = "low", "Baixa"
        MEDIUM = "medium", "Média"
        HIGH = "high", "Alta"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        REVIEWED = "reviewed", "Analisada"
        PLANNED = "planned", "Planejada"
        IMPLEMENTED = "implemented", "Implementada"
        DECLINED = "declined", "Recusada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="suggestions",
        verbose_name="Usuário",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.FEATURE,
        verbose_name="Categoria",
    )
    title = models.CharField(max_length=200, verbose_name="Título")
    description = models.TextField(verbose_name="Descrição")
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Prioridade",
        help_text="Definida internamente pela equipe",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name="Notas internas",
        help_text="Notas da equipe sobre esta sugestão (invisível ao usuário)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última atualização")

    class Meta:
        verbose_name = "Sugestão de Melhoria"
        verbose_name_plural = "Sugestões de Melhoria"
        ordering = ["-created_at"]

    def __str__(self):
        user_label = self.user.username if self.user else "Anônimo"
        return f"[{self.get_category_display()}] {self.title} — {user_label}"
