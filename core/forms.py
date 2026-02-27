"""
core/forms.py — Formulários para upload de documentos, configuração de análise e sugestões.
"""

from django import forms
from .models import AnalysisRequest, Suggestion


INPUT_CLASSES = (
    "w-full px-3 py-2.5 border border-gray-300 rounded-lg "
    "focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
)

SELECT_CLASSES = (
    "w-full px-3 py-2.5 border border-gray-300 rounded-lg "
    "focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm bg-white"
)

TEXTAREA_CLASSES = (
    "w-full px-3 py-2.5 border border-gray-300 rounded-lg "
    "focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-y"
)

CHECKBOX_CLASSES = (
    "w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded "
    "focus:ring-blue-500 focus:ring-2"
)

RANGE_CLASSES = (
    "w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
)


class DocumentUploadForm(forms.Form):
    """Formulário de upload de documento (aceita múltiplos arquivos)."""
    
    file = forms.FileField(
        label="Documento",
        required=False,  # Not required for free-form mode
        widget=forms.FileInput(attrs={
            "class": "hidden",
            "id": "file-input",
            "accept": ".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.csv,.md,.html,.htm,.png,.jpg,.jpeg,.gif,.bmp,.tiff",
        }),
        help_text="PDF, DOCX, XLSX, PPTX, TXT, CSV, imagens e mais",
    )


class AnalysisConfigForm(forms.Form):
    """Formulário de configuração da análise — com modos expandidos."""
    
    analysis_mode = forms.ChoiceField(
        label="Modo de Análise",
        choices=AnalysisRequest.AnalysisMode.choices,
        initial=AnalysisRequest.AnalysisMode.DOCUMENT,
        widget=forms.HiddenInput(attrs={"id": "id_analysis_mode"}),
    )
    
    user_objective = forms.CharField(
        label="O que você quer analisar?",
        widget=forms.Textarea(attrs={
            "class": TEXTAREA_CLASSES,
            "rows": 4,
            "placeholder": "Descreva com suas palavras o que você busca nesta análise. "
                          "Ex: 'Quero entender os riscos financeiros deste contrato e comparar com as práticas de mercado'",
        }),
        help_text="Quanto mais detalhado, melhor o Joel entenderá seu objetivo",
    )
    
    professional_area = forms.ChoiceField(
        label="Área Profissional",
        choices=AnalysisRequest.ProfessionalArea.choices,
        initial=AnalysisRequest.ProfessionalArea.OUTRO,
        widget=forms.Select(attrs={"class": SELECT_CLASSES}),
    )
    
    professional_area_detail = forms.CharField(
        label="Detalhe a área (opcional)",
        required=False,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Ex: 'Protocolo de estética facial', 'Contrato de franquia', 'Plano de treino funcional'",
        }),
        help_text="Descreva a área com suas palavras para ajudar o Joel a ser mais assertivo",
    )
    
    geolocation = forms.CharField(
        label="Geolocalização das Referências",
        required=False,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASSES,
            "placeholder": "Ex: Brasil, São Paulo — ou Global para busca mundial",
        }),
        help_text="Onde buscar referências de mercado? País, estado ou região",
    )
    
    language = forms.ChoiceField(
        label="Idioma do Relatório",
        choices=AnalysisRequest.Language.choices,
        initial=AnalysisRequest.Language.PT_BR,
        widget=forms.Select(attrs={"class": SELECT_CLASSES}),
    )
    
    include_market_references = forms.BooleanField(
        label="Incluir referências de mercado",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CLASSES}),
        help_text="O Joel pesquisará na internet por benchmarks e referências atuais",
    )
    
    source_count = forms.IntegerField(
        label="Quantidade de fontes",
        initial=5,
        min_value=1,
        max_value=20,
        widget=forms.NumberInput(attrs={
            "class": INPUT_CLASSES,
            "type": "range",
            "min": "1",
            "max": "20",
            "step": "1",
            "id": "id_source_count",
        }),
        help_text="Quantas fontes/referências incluir no relatório",
    )
    
    include_images = forms.BooleanField(
        label="Incluir imagens no relatório",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CLASSES}),
        help_text="Joel incluirá imagens profissionais e ilustrações geradas por IA",
    )
    
    search_scope = forms.CharField(
        label="Escopo adicional de busca (opcional)",
        required=False,
        widget=forms.Textarea(attrs={
            "class": TEXTAREA_CLASSES,
            "rows": 2,
            "placeholder": "Palavras-chave extras para direcionar a pesquisa. Ex: 'ANVISA regulamentação 2025'",
        }),
        help_text="Palavras-chave adicionais para refinar a busca na internet",
    )
    
    report_type = forms.ChoiceField(
        label="Tipo de Relatório",
        choices=AnalysisRequest.ReportType.choices,
        initial=AnalysisRequest.ReportType.ANALITICO,
        widget=forms.Select(attrs={"class": SELECT_CLASSES}),
    )


class SuggestionForm(forms.ModelForm):
    """Formulário para sugestões de melhoria — simples e rápido."""

    class Meta:
        model = Suggestion
        fields = ["category", "title", "description"]
        widgets = {
            "category": forms.Select(attrs={
                "class": SELECT_CLASSES,
            }),
            "title": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Título da sugestão",
                "maxlength": "200",
            }),
            "description": forms.Textarea(attrs={
                "class": TEXTAREA_CLASSES,
                "rows": 2,
                "placeholder": "Descreva com detalhes o que gostaria de ver na plataforma...",
            }),
        }
