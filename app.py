from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente conforme ambiente alvo.
APP_ENV = (os.environ.get("APP_ENV") or os.environ.get("ERP_ENV") or "development").strip().lower()
ENV_FILE_BY_APP_ENV = {
    "development": ".env",
    "homolog": ".env.homolog",
    "staging": ".env.homolog",
    "production": ".env.production",
}

selected_env_file = ENV_FILE_BY_APP_ENV.get(APP_ENV, ".env")
load_dotenv(selected_env_file)
if selected_env_file != ".env":
    # Permite fallback de variáveis locais compartilhadas sem sobrescrever as específicas.
    load_dotenv(".env")

from models import (
    authenticate_user,
    create_account_with_owner,
    get_db_connection,
    init_auth_db,
    init_tenant_db,
    migrate_legacy_database,
    seed_admin,
    seed_all_accounts_default_data,
)

# Importação dos blueprints deve ser feita após a definição do app e models
try:
    from export_report import export_bp
except ImportError:
    export_bp = None
    print("⚠️  export_report não disponível (requer pandas)")

try:
    from generate_po_pdf import generate_po_pdf_bp
except ImportError:
    generate_po_pdf_bp = None
    print("⚠️  generate_po_pdf não disponível")

try:
    from import_excel import import_excel_bp
except ImportError:
    import_excel_bp = None
    print("⚠️  import_excel não disponível (requer pandas)")

from access_control import access_bp
from logs_auditoria import auditoria_bp, log_audit_event
        total_clients = 0
        total_products = 0
        total_sales = 0
from datetime import datetime, timedelta
from calendar import monthrange
import re
import json
import logging
import smtplib
import unicodedata
import xml.etree.ElementTree as ET
from email.message import EmailMessage

# Importar psycopg para PostgreSQL (opcional em desenvolvimento)
try:
    import psycopg
except ImportError:
    psycopg = None
    print("⚠️  psycopg não disponível - usando SQLite para desenvolvimento local")

logger = logging.getLogger(__name__)


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "kdc_systems_secret_key")

# Registrar blueprints disponíveis
if export_bp:
    app.register_blueprint(export_bp)
if generate_po_pdf_bp:
    app.register_blueprint(generate_po_pdf_bp)
if import_excel_bp:
    app.register_blueprint(import_excel_bp)
app.register_blueprint(access_bp)
app.register_blueprint(auditoria_bp)

LANGUAGES = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "zh": "中文"
}

TRANSLATIONS = {
    "pt": {
        "login_title": "Entrar no Kdc Systems",
        "username_label": "Usuário",
        "password_label": "Senha",
        "email_label": "E-mail",
        "dashboard_title": "Painel de controle",
        "dashboard_welcome": "Bem-vindo(a)",
        "menu_dashboard": "Dashboard",
        "menu_users": "Usuários",
        "menu_products": "Produtos",
        "menu_clients": "Clientes",
        "menu_suppliers": "Fornecedores",
        "menu_sales": "Vendas",
        "menu_reports": "Relatórios",
        "menu_finance": "Financeiro",
        "menu_manual": "Documentação",
        "menu_logout": "Sair",
        "user_list": "Lista de usuários",
        "add_user": "Adicionar usuário",
        "reset_password_button": "Reiniciar senha",
        "new_password_placeholder": "Nova senha",
        "no_records_found": "Nenhum registro encontrado",
        "product_name": "Produto / Serviço",
        "category_label": "Categoria",
        "unit_label": "Unidade de medida",
        "cost_label": "Preço de custo",
        "price_label": "Preço de venda",
        "stock_label": "Estoque",
        "stock_min_label": "Estoque mínimo",
        "expiration_date": "Validade",
        "add_product": "Adicionar produto",
        "product_list": "Lista de produtos",
        "client_name": "Nome do cliente",
        "cpf_label": "CPF",
        "address_label": "Endereço",
        "street_label": "Logradouro",
        "search_placeholder": "Pesquisar...",
        "number_label": "Número",
        "complement_label": "Complemento",
        "neighborhood_label": "Bairro",
        "city_label": "Cidade",
        "state_label": "UF",
        "country_label": "País",
        "zipcode_label": "CEP",
        "add_client": "Adicionar cliente",
        "add_category": "Adicionar categoria",
        "new_category_prompt": "Nova categoria",
        "new_unit_prompt": "Nova unidade",
        "manage_categories": "Gerenciar categorias",
        "manage_units": "Gerenciar unidades",
        "back_to_products": "Voltar para Produtos",
        "client_list": "Lista de clientes",
        "supplier_name": "Fornecedor",
        "cnpj_label": "CNPJ",
        "supplier_category": "Categoria do fornecedor",
        "add_supplier": "Adicionar fornecedor",
        "supplier_list": "Lista de fornecedores",
        "add_category": "Adicionar categoria",
        "category_list": "Lista de categorias",
        "add_unit": "Adicionar unidade",
        "unit_list": "Lista de unidades",
        "product_label": "Produto",
        "select_product": "Selecione um produto",
        "quantity_label": "Quantidade",
        "unit_price": "Preço unitário",
        "line_total": "Total por produto",
        "remove": "Remover",
        "add_item": "Adicionar item",
        "discount_label": "Desconto",
        "surcharge_label": "Acréscimo",
        "payment_method": "Forma de pagamento",
        "payment_received": "Valor recebido",
        "client_label": "Cliente",
        "no_client": "Sem cliente",
        "total_label": "Total da venda",
        "cash_change": "Troco",
        "confirm_sale_button": "Confirmar venda",
        "pix_code_title": "Código Pix",
        "close_cash": "Fechar caixa",
        "cash_summary_title": "Resumo do caixa",
        "cash_total_message": "Total em dinheiro do dia:",
        "email_sent_to": "E-mail enviado para",
        "email_not_configured": "E-mail não configurado.",
        "manual_title": "Documentação do sistema",
        "manual_intro": "Este manual apresenta os principais processos do sistema Kdc Systems.",
        "manual_login": "Faça login com usuário e senha para acessar o sistema.",
        "manual_register": "Cadastre produtos, clientes, fornecedores, categorias e unidades.",
        "manual_sales": "Registre vendas com desconto, acréscimo e cálculo de troco.",
        "manual_reports": "Use relatórios para acompanhar vendas, estoque e lucro.",
        "manual_language": "Altere o idioma do sistema no menu superior.",
        "manual_footer": "Para dúvidas, use a documentação interna e mantenha seus cadastros atualizados.",
        "period_start": "Data de início",
        "period_end": "Data de término",
        "apply_filter": "Aplicar filtro",
        "report_period": "Período do relatório",
        "sales_by_period": "Vendas no período",
        "sale_date": "Data",
        "suppliers_report_card": "Relatório por fornecedor",
        "clients_report_card": "Relatório por cliente",
        "products_report_card": "Relatório por produto",
        "categories_report_card": "Relatório por categoria",
        "report_choose_type": "Escolha um tipo de relatório",
        "supplier_by_category": "Fornecedores por categoria",
        "supplier_by_category_desc": "Total de fornecedores organizados por categoria.",
        "supplier_product_quantity": "Quantidade de produtos vendidos por fornecedor",
        "supplier_product_quantity_desc": "Quantidades vendidas agrupadas por fornecedor (dados não vinculados no cadastro atual).",
        "supplier_sales_value": "Valor total de vendas por fornecedor",
        "supplier_sales_value_desc": "Valor de vendas por fornecedor (dados não vinculados no cadastro atual).",
        "client_sales_quantity": "Quantidade vendida por cliente",
        "client_sales_quantity_desc": "Total de itens vendidos por cliente.",
        "client_sales_value": "Valor total de vendas por cliente",
        "client_sales_value_desc": "Valor de vendas por cliente.",
        "product_sales_quantity": "Quantidade vendida por produto",
        "product_sales_quantity_desc": "Total de itens vendidos por produto.",
        "product_sales_value": "Valor total de vendas por produto",
        "product_sales_value_desc": "Valor de vendas por produto.",
        "category_sales_quantity": "Quantidade vendida por categoria",
        "category_sales_quantity_desc": "Total de itens vendidos por categoria de produto.",
        "category_sales_value": "Valor total de vendas por categoria",
        "category_sales_value_desc": "Valor de vendas por categoria de produto.",
        "report_not_available": "Dados não disponíveis para este relatório com a modelagem atual.",
        "view_report": "Ver relatório",
        "back_to_reports": "Voltar aos relatórios",
        "stock_report": "Relatório de estoque",
        "highest_stock": "Maior estoque",
        "lowest_stock": "Menor estoque",
        "top_customers": "Clientes que mais compram",
        "product_profit_top": "Produtos com maior lucro",
        "payment_report": "Vendas por forma de pagamento",
        "unknown": "Desconhecido",
        "error_required_fields": "Preencha todos os campos obrigatórios.",
        "invalid_login": "Usuário ou senha inválidos.",
        "sale_success": "Venda registrada com sucesso.",
        "error_insufficient_stock": "Estoque insuficiente para o produto selecionado.",
        "error_no_items": "Adicione pelo menos um item na venda.",
        "error_invalid_date": "Data inválida.",
        "dashboard_welcome_text": "Gerencie seu negócio com eficiência: controle operações, acompanhe resultados e tome decisões com segurança.",
        "manual_access": "Acesse o manual pelo menu.",
        "select_language": "Idioma",
        "record_saved": "Registro salvo com sucesso.",
        "name_label": "Nome",
        "forgot_password_label": "Esqueci minha senha",
        "payments_report_card": "Relatório por forma de pagamento",
        "payment_sales_value": "Valor total de vendas por forma de pagamento",
        "payment_sales_value_desc": "Valor de vendas por forma de pagamento.",
        "sales_period_report_card": "Vendas no período",
        "sales_period_desc": "Lista de vendas realizadas no período selecionado.",
        "actions": "Ações",
        "product_net_profit": "Lucro líquido",
        "gender_label": "Gênero",
        "gender_male": "Masculino",
        "gender_female": "Feminino",
        "gender_not_informed": "Não informar",
        "stock_current_quantity": "Quantidade atual",
        "near_min_stock": "Produtos mais próximos do estoque mínimo",
        "total_sum": "Total geral",
        "product_gender_share": "Vendas por produto e percentual por gênero"
    },
    "en": {
        "login_title": "Kdc Systems Login",
        "username_label": "Username",
        "password_label": "Password",
        "email_label": "Email",
        "dashboard_title": "Dashboard",
        "dashboard_welcome": "Welcome",
        "menu_dashboard": "Dashboard",
        "menu_users": "Users",
        "menu_products": "Products",
        "menu_clients": "Clients",
        "menu_suppliers": "Suppliers",
        "menu_sales": "Sales",
        "menu_reports": "Reports",
        "menu_manual": "Manual",
        "menu_finance": "Finance",
        "menu_logout": "Logout",
        "user_list": "User list",
        "add_user": "Add user",
        "reset_password_button": "Reset password",
        "new_password_placeholder": "New password",
        "no_records_found": "No records found",
        "product_name": "Product / Service",
        "category_label": "Category",
        "unit_label": "Unit",
        "cost_label": "Cost",
        "price_label": "Sales price",
        "stock_label": "Stock",
        "stock_min_label": "Minimum stock",
        "expiration_date": "Expiration date",
        "add_product": "Add product",
        "product_list": "Product list",
        "client_name": "Client name",
        "cpf_label": "CPF",
        "address_label": "Address",
        "street_label": "Street",
        "number_label": "Number",
        "complement_label": "Complement",
        "neighborhood_label": "Neighborhood",
        "city_label": "City",
        "state_label": "State",
        "country_label": "Country",
        "zipcode_label": "Postal code",
        "add_category": "Add category",
        "new_category_prompt": "New category",
        "client_list": "Client list",
        "supplier_name": "Supplier",
        "cnpj_label": "CNPJ",
        "supplier_category": "Supplier category",
        "add_supplier": "Add supplier",
        "supplier_list": "Supplier list",
        "add_category": "Add category",
        "new_category_prompt": "New category",
        "new_unit_prompt": "New unit",
        "manage_categories": "Manage categories",
        "manage_units": "Manage units",
        "back_to_products": "Back to Products",
        "category_list": "Category list",
        "add_unit": "Add unit",
        "unit_list": "Unit list",
        "product_label": "Product",
        "select_product": "Select a product",
        "quantity_label": "Quantity",
        "unit_price": "Unit price",
        "line_total": "Line total",
        "remove": "Remove",
        "add_item": "Add item",
        "discount_label": "Discount",
        "surcharge_label": "Surcharge",
        "payment_method": "Payment method",
        "payment_received": "Amount received",
        "client_label": "Client",
        "no_client": "No client",
        "total_label": "Order total",
        "cash_change": "Change",
        "confirm_sale_button": "Confirm sale",
        "pix_code_title": "Pix code",
        "close_cash": "Close register",
        "cash_summary_title": "Cash summary",
        "cash_total_message": "Cash total today:",
        "email_sent_to": "Email sent to",
        "email_not_configured": "Email not configured.",
        "manual_title": "User manual",
        "manual_intro": "This manual explains the main processes of Kdc Systems.",
        "manual_login": "Log in with username and password to access the system.",
        "manual_register": "Register products, clients, suppliers, categories and units.",
        "manual_sales": "Record sales with discount, surcharge and change calculation.",
        "manual_reports": "Use reports to monitor sales, stock and profit.",
        "manual_language": "Change the system language in the top menu.",
        "manual_footer": "For questions, use the internal documentation and keep your data updated.",
        "period_start": "Start date",
        "period_end": "End date",
        "apply_filter": "Apply filter",
        "sales_by_period": "Sales by period",
        "sale_date": "Date",
        "stock_report": "Stock report",
        "highest_stock": "Highest stock",
        "lowest_stock": "Lowest stock",
        "top_customers": "Top customers",
        "product_profit_top": "Top profit products",
        "payment_report": "Payment report",
        "unknown": "Unknown",
        "error_required_fields": "Fill in all required fields.",
        "invalid_login": "Invalid username or password.",
        "sale_success": "Sale recorded successfully.",
        "error_insufficient_stock": "Insufficient stock for selected product.",
        "error_no_items": "Add at least one item to the sale.",
        "error_invalid_date": "Invalid date.",
        "dashboard_welcome_text": "Use the menu to access registrations, sales, reports and manual.",
        "manual_access": "Access the manual from the menu.",
        "select_language": "Language",
        "record_saved": "Record saved successfully.",
        "name_label": "Name",
        "forgot_password_label": "Forgot my password",
        "payments_report_card": "Payment method report",
        "payment_sales_value": "Total sales value by payment method",
        "payment_sales_value_desc": "Sales value by payment method.",
        "sales_period_report_card": "Sales in period",
        "sales_period_desc": "List of sales made in the selected period.",
        "actions": "Actions"
    },
    "es": {
        "login_title": "Inicio de sesión Kdc Systems",
        "username_label": "Usuario",
        "password_label": "Contraseña",
        "email_label": "Correo electrónico",
        "dashboard_title": "Panel",
        "dashboard_welcome": "Bienvenido",
        "menu_dashboard": "Panel",
        "menu_users": "Usuarios",
        "menu_products": "Productos",
        "menu_clients": "Clientes",
        "menu_suppliers": "Proveedores",
        "menu_sales": "Ventas",
        "menu_reports": "Informes",
        "menu_manual": "Manual",
        "menu_finance": "Finanzas",
        "menu_logout": "Salir",
        "user_list": "Lista de usuarios",
        "add_user": "Agregar usuario",
        "reset_password_button": "Restablecer contraseña",
        "new_password_placeholder": "Nueva contraseña",
        "no_records_found": "No se encontraron registros",
        "product_name": "Producto / Servicio",
        "category_label": "Categoría",
        "unit_label": "Unidad",
        "cost_label": "Costo",
        "price_label": "Precio de venta",
        "stock_label": "Stock",
        "stock_min_label": "Stock mínimo",
        "expiration_date": "Vencimiento",
        "add_product": "Agregar producto",
        "product_list": "Lista de productos",
        "client_name": "Nombre del cliente",
        "cpf_label": "CPF",
        "address_label": "Dirección",
        "zipcode_label": "Código postal",
        "add_client": "Agregar cliente",
        "client_list": "Lista de clientes",
        "supplier_name": "Proveedor",
        "cnpj_label": "CNPJ",
        "supplier_category": "Categoría del proveedor",
        "add_supplier": "Agregar proveedor",
        "supplier_list": "Lista de proveedores",
        "add_category": "Agregar categoría",
        "category_list": "Lista de categorías",
        "add_unit": "Agregar unidad",
        "unit_list": "Lista de unidades",
        "product_label": "Producto",
        "select_product": "Selecciona un producto",
        "quantity_label": "Cantidad",
        "unit_price": "Precio unitario",
        "line_total": "Total",
        "remove": "Eliminar",
        "add_item": "Agregar ítem",
        "discount_label": "Descuento",
        "surcharge_label": "Recargo",
        "payment_method": "Forma de pago",
        "payment_received": "Valor recibido",
        "client_label": "Cliente",
        "no_client": "Sin cliente",
        "total_label": "Total de la venta",
        "cash_change": "Cambio",
        "confirm_sale_button": "Confirmar venta",
        "pix_code_title": "Código Pix",
        "close_cash": "Cerrar caja",
        "cash_summary_title": "Resumen de caja",
        "cash_total_message": "Total en efectivo hoy:",
        "email_sent_to": "Correo enviado a",
        "email_not_configured": "Correo no configurado.",
        "manual_title": "Manual de uso",
        "manual_intro": "Este manual explica los procesos principales del sistema Kdc Systems.",
        "manual_login": "Inicia sesión con usuario y contraseña para acceder al sistema.",
        "manual_register": "Registra productos, clientes, proveedores, categorías y unidades.",
        "manual_sales": "Registra ventas con descuento, recargo y cálculo de cambio.",
        "manual_reports": "Usa informes para monitorear ventas, stock y ganancias.",
        "manual_language": "Cambia el idioma del sistema en el menú superior.",
        "manual_footer": "Para dudas, usa la documentación interna y mantén tus datos actualizados.",
        "period_start": "Fecha inicio",
        "period_end": "Fecha fin",
        "apply_filter": "Aplicar filtro",
        "sales_by_period": "Ventas por periodo",
        "sale_date": "Fecha",
        "stock_report": "Informe de stock",
        "highest_stock": "Mayor stock",
        "lowest_stock": "Menor stock",
        "top_customers": "Clientes top",
        "product_profit_top": "Productos con mayor ganancia",
        "payment_report": "Reporte de pagos",
        "unknown": "Desconocido",
        "error_required_fields": "Complete todos los campos obligatorios.",
        "invalid_login": "Usuario o contraseña inválidos.",
        "sale_success": "Venta registrada con éxito.",
        "error_insufficient_stock": "Stock insuficiente para el producto seleccionado.",
        "error_no_items": "Agrega al menos un ítem a la venta.",
        "error_invalid_date": "Fecha inválida.",
        "dashboard_welcome_text": "Usa el menú para acceder a registros, ventas, informes y manual.",
        "manual_access": "Accede al manual desde el menú.",
        "select_language": "Idioma",
        "record_saved": "Registro guardado con éxito.",
        "name_label": "Nombre",
        "forgot_password_label": "Olvidé mi contraseña",
        "actions": "Acciones"
    },
    "fr": {
        "login_title": "Connexion Kdc Systems",
        "username_label": "Nom d'utilisateur",
        "password_label": "Mot de passe",
        "email_label": "Email",
        "dashboard_title": "Tableau de bord",
        "dashboard_welcome": "Bienvenue",
        "menu_dashboard": "Tableau",
        "menu_users": "Utilisateurs",
        "menu_products": "Produits",
        "menu_clients": "Clients",
        "menu_suppliers": "Fournisseurs",
        "menu_sales": "Ventes",
        "menu_reports": "Rapports",
        "menu_manual": "Manuel",
        "menu_finance": "Finances",
        "menu_logout": "Déconnexion",
        "user_list": "Liste des utilisateurs",
        "add_user": "Ajouter un utilisateur",
        "reset_password_button": "Réinitialiser le mot de passe",
        "new_password_placeholder": "Nouveau mot de passe",
        "no_records_found": "Aucun enregistrement trouvé",
        "product_name": "Produit / Service",
        "category_label": "Catégorie",
        "unit_label": "Unité",
        "cost_label": "Coût",
        "price_label": "Prix de vente",
        "stock_label": "Stock",
        "stock_min_label": "Stock minimum",
        "expiration_date": "Expiration",
        "add_product": "Ajouter produit",
        "product_list": "Liste de produits",
        "client_name": "Nom du client",
        "cpf_label": "CPF",
        "address_label": "Adresse",
        "zipcode_label": "Code postal",
        "add_client": "Ajouter client",
        "client_list": "Liste de clients",
        "supplier_name": "Fournisseur",
        "cnpj_label": "CNPJ",
        "supplier_category": "Catégorie fournisseur",
        "add_supplier": "Ajouter fournisseur",
        "supplier_list": "Liste des fournisseurs",
        "add_category": "Ajouter catégorie",
        "category_list": "Liste des catégories",
        "add_unit": "Ajouter unité",
        "unit_list": "Liste des unités",
        "product_label": "Produit",
        "select_product": "Sélectionnez un produit",
        "quantity_label": "Quantité",
        "unit_price": "Prix unitaire",
        "line_total": "Total ligne",
        "remove": "Supprimer",
        "add_item": "Ajouter un article",
        "discount_label": "Remise",
        "surcharge_label": "Supplément",
        "payment_method": "Mode de paiement",
        "payment_received": "Montant reçu",
        "client_label": "Client",
        "no_client": "Aucun client",
        "total_label": "Total",
        "cash_change": "Monnaie",
        "confirm_sale_button": "Confirmer la vente",
        "pix_code_title": "Code Pix",
        "close_cash": "Fermer la caisse",
        "cash_summary_title": "Résumé de caisse",
        "cash_total_message": "Total en espèces aujourd'hui:",
        "email_sent_to": "E-mail envoyé à",
        "email_not_configured": "E-mail non configuré.",
        "manual_title": "Manuel d'utilisation",
        "manual_intro": "Ce manuel explique les principaux processus de Kdc Systems.",
        "manual_login": "Connectez-vous avec votre nom d'utilisateur et mot de passe.",
        "manual_register": "Enregistrez produits, clients, fournisseurs, catégories et unités.",
        "manual_sales": "Enregistrez les ventes avec remise, supplément et calcul de monnaie.",
        "manual_reports": "Utilisez les rapports pour suivre ventes, stock et profit.",
        "manual_language": "Changez la langue du système dans le menu supérieur.",
        "manual_footer": "Pour des questions, utilisez la documentation interne.",
        "period_start": "Date de début",
        "period_end": "Date de fin",
        "apply_filter": "Appliquer",
        "sales_by_period": "Ventes par période",
        "sale_date": "Date",
        "stock_report": "Rapport de stock",
        "highest_stock": "Stock le plus élevé",
        "lowest_stock": "Stock le plus bas",
        "top_customers": "Clients principaux",
        "product_profit_top": "Produits les plus rentables",
        "payment_report": "Rapport de paiement",
        "unknown": "Inconnu",
        "error_required_fields": "Remplissez tous les champs obligatoires.",
        "invalid_login": "Nom d'utilisateur ou mot de passe invalide.",
        "sale_success": "Vente enregistrée avec succès.",
        "error_insufficient_stock": "Stock insuffisant pour le produit sélectionné.",
        "error_no_items": "Ajoutez au moins un article à la vente.",
        "error_invalid_date": "Date invalide.",
        "dashboard_welcome_text": "Utilisez le menu pour accéder aux enregistrements, ventes, rapports et manuel.",
        "manual_access": "Accédez au manuel depuis le menu.",
        "select_language": "Langue",
        "record_saved": "Enregistrement sauvegardé avec succès.",
        "name_label": "Nom",
        "forgot_password_label": "J'ai oublié mon mot de passe",
        "actions": "Actions"
    },
    "de": {
        "login_title": "Kdc Systems Anmeldung",
        "username_label": "Benutzer",
        "password_label": "Passwort",
        "email_label": "E-Mail",
        "dashboard_title": "Dashboard",
        "dashboard_welcome": "Willkommen",
        "menu_dashboard": "Dashboard",
        "menu_users": "Benutzer",
        "menu_products": "Produkte",
        "menu_clients": "Kunden",
        "menu_suppliers": "Lieferanten",
        "menu_sales": "Verkäufe",
        "menu_reports": "Berichte",
        "menu_manual": "Handbuch",
        "menu_finance": "Finanzen",
        "menu_logout": "Abmelden",
        "user_list": "Benutzerliste",
        "add_user": "Benutzer hinzufügen",
        "reset_password_button": "Passwort zurücksetzen",
        "new_password_placeholder": "Neues Passwort",
        "no_records_found": "Keine Einträge gefunden",
        "product_name": "Produkt / Dienstleistung",
        "category_label": "Kategorie",
        "unit_label": "Einheit",
        "cost_label": "Kosten",
        "price_label": "Verkaufspreis",
        "stock_label": "Lager",
        "stock_min_label": "Mindestbestand",
        "expiration_date": "Verfallsdatum",
        "add_product": "Produkt hinzufügen",
        "product_list": "Produktliste",
        "client_name": "Kundenname",
        "cpf_label": "CPF",
        "address_label": "Adresse",
        "zipcode_label": "PLZ",
        "add_client": "Kunden hinzufügen",
        "client_list": "Kundenliste",
        "supplier_name": "Lieferant",
        "cnpj_label": "CNPJ",
        "supplier_category": "Lieferantenkategorie",
        "add_supplier": "Lieferant hinzufügen",
        "supplier_list": "Lieferantenliste",
        "add_category": "Kategorie hinzufügen",
        "category_list": "Kategorienliste",
        "add_unit": "Einheit hinzufügen",
        "unit_list": "Einheitenliste",
        "product_label": "Produkt",
        "select_product": "Produkt wählen",
        "quantity_label": "Menge",
        "unit_price": "Stückpreis",
        "line_total": "Zeilensumme",
        "remove": "Entfernen",
        "add_item": "Artikel hinzufügen",
        "discount_label": "Rabatt",
        "surcharge_label": "Aufschlag",
        "payment_method": "Zahlungsart",
        "payment_received": "Erhaltener Betrag",
        "client_label": "Kunde",
        "no_client": "Kein Kunde",
        "total_label": "Gesamtsumme",
        "cash_change": "Rückgeld",
        "confirm_sale_button": "Verkauf bestätigen",
        "pix_code_title": "Pix-Code",
        "close_cash": "Kasse schließen",
        "cash_summary_title": "Kassenübersicht",
        "cash_total_message": "Bargeldsumme heute:",
        "email_sent_to": "E-Mail gesendet an",
        "email_not_configured": "E-Mail nicht konfiguriert.",
        "manual_title": "Benutzerhandbuch",
        "manual_intro": "Dieses Handbuch erklärt die Hauptprozesse von Kdc Systems.",
        "manual_login": "Melden Sie sich an, um das System zu nutzen.",
        "manual_register": "Registrieren Sie Produkte, Kunden, Lieferanten, Kategorien und Einheiten.",
        "manual_sales": "Erfassen Sie Verkäufe mit Rabatt, Aufschlag und Rückgeldberechnung.",
        "manual_reports": "Verwenden Sie Berichte zur Überwachung von Verkäufen, Lager und Gewinn.",
        "manual_language": "Ändern Sie die Systemsprache im oberen Menü.",
        "manual_footer": "Bei Fragen nutzen Sie die interne Dokumentation.",
        "period_start": "Startdatum",
        "period_end": "Enddatum",
        "apply_filter": "Filter anwenden",
        "sales_by_period": "Verkäufe im Zeitraum",
        "sale_date": "Datum",
        "stock_report": "Lagerbericht",
        "highest_stock": "Höchster Lagerbestand",
        "lowest_stock": "Niedrigster Lagerbestand",
        "top_customers": "Top-Kunden",
        "product_profit_top": "Produkte mit höchstem Gewinn",
        "payment_report": "Zahlungsbericht",
        "unknown": "Unbekannt",
        "error_required_fields": "Füllen Sie alle Pflichtfelder aus.",
        "invalid_login": "Ungültiger Benutzername oder Passwort.",
        "sale_success": "Verkauf erfolgreich erfasst.",
        "error_insufficient_stock": "Nicht genügend Lagerbestand für das ausgewählte Produkt.",
        "error_no_items": "Fügen Sie mindestens einen Artikel zur Bestellung hinzu.",
        "error_invalid_date": "Ungültiges Datum.",
        "dashboard_welcome_text": "Verwenden Sie das Menü, um auf Registrierungen, Verkäufe, Berichte und Handbuch zuzugreifen.",
        "manual_access": "Greifen Sie über das Menü auf das Handbuch zu.",
        "select_language": "Sprache",
        "record_saved": "Datensatz erfolgreich gespeichert.",
        "name_label": "Name",
        "forgot_password_label": "Passwort vergessen",
        "actions": "Aktionen"
    },
    "zh": {
        "login_title": "Kdc Systems 登录",
        "username_label": "用户名",
        "password_label": "密码",
        "email_label": "电子邮件",
        "dashboard_title": "仪表盘",
        "dashboard_welcome": "欢迎",
        "menu_dashboard": "仪表盘",
        "menu_users": "用户",
        "menu_products": "产品",
        "menu_clients": "客户",
        "menu_suppliers": "供应商",
        "menu_sales": "销售",
        "menu_reports": "报表",
        "menu_manual": "手册",
        "menu_finance": "财务",
        "menu_logout": "退出",
        "user_list": "用户列表",
        "add_user": "添加用户",
        "reset_password_button": "重置密码",
        "new_password_placeholder": "新密码",
        "no_records_found": "未找到记录",
        "product_name": "产品/服务",
        "category_label": "类别",
        "unit_label": "单位",
        "cost_label": "成本",
        "price_label": "售价",
        "stock_label": "库存",
        "stock_min_label": "最低库存",
        "expiration_date": "有效期",
        "add_product": "添加产品",
        "product_list": "产品列表",
        "client_name": "客户姓名",
        "cpf_label": "CPF",
        "address_label": "地址",
        "zipcode_label": "邮编",
        "add_client": "添加客户",
        "client_list": "客户列表",
        "supplier_name": "供应商",
        "cnpj_label": "CNPJ",
        "supplier_category": "供应商类别",
        "add_supplier": "添加供应商",
        "supplier_list": "供应商列表",
        "add_category": "添加类别",
        "category_list": "类别列表",
        "add_unit": "添加单位",
        "unit_list": "单位列表",
        "product_label": "产品",
        "select_product": "选择产品",
        "quantity_label": "数量",
        "unit_price": "单价",
        "line_total": "行总计",
        "remove": "删除",
        "add_item": "添加项目",
        "discount_label": "折扣",
        "surcharge_label": "附加费",
        "payment_method": "支付方式",
        "payment_received": "收到金额",
        "client_label": "客户",
        "no_client": "无客户",
        "total_label": "订单总计",
        "cash_change": "找零",
        "confirm_sale_button": "确认销售",
        "pix_code_title": "Pix 代码",
        "close_cash": "结算",
        "cash_summary_title": "收银总结",
        "cash_total_message": "今日现金总计:",
        "email_sent_to": "已发送电子邮件至",
        "email_not_configured": "电子邮件未配置。",
        "manual_title": "使用手册",
        "manual_intro": "本手册介绍 Kdc Systems 的主要流程。",
        "manual_login": "使用用户名和密码登录系统。",
        "manual_register": "注册产品、客户、供应商、类别和单位。",
        "manual_sales": "记录销售，包含折扣、附加费和找零计算。",
        "manual_reports": "使用报表监控销售、库存和利润。",
        "manual_language": "在顶部菜单更改系统语言。",
        "manual_footer": "如有疑问，请使用内部文档并保持数据更新。",
        "period_start": "开始日期",
        "period_end": "结束日期",
        "apply_filter": "应用过滤",
        "sales_by_period": "期间销售",
        "sale_date": "日期",
        "stock_report": "库存报告",
        "highest_stock": "最高库存",
        "lowest_stock": "最低库存",
        "top_customers": "最佳客户",
        "product_profit_top": "最高利润产品",
        "payment_report": "支付报告",
        "unknown": "未知",
        "error_required_fields": "请填写所有必填字段。",
        "invalid_login": "用户名或密码无效。",
        "sale_success": "销售记录成功。",
        "error_insufficient_stock": "所选产品库存不足。",
        "error_no_items": "至少添加一个销售项目。",
        "error_invalid_date": "无效日期。",
        "dashboard_welcome_text": "使用菜单访问注册、销售、报表和手册。",
        "manual_access": "从菜单访问手册。",
        "select_language": "语言",
        "record_saved": "记录保存成功。",
        "name_label": "名称",
        "forgot_password_label": "忘记了我的密码",
        "actions": "操作"
    }
}
DEFAULT_LANG = "pt"


def translate(key):
    lang = session.get("lang", DEFAULT_LANG)
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG]).get(key, TRANSLATIONS[DEFAULT_LANG].get(key, key))


def normalize_date_for_input(value):
    if not value:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    # Keep only the date segment when datetime-like values are stored.
    text = text.split(" ")[0]

    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


@app.context_processor
def inject_translations():
    permissions = get_current_user_permissions() if session.get("user") else {}
    return {
        "t": lambda key: translate(key),
        "languages": LANGUAGES,
        "current_language": session.get("lang", DEFAULT_LANG),
        "current_permissions": permissions,
        "can_access": lambda module_key: user_can_view_module(module_key),
        "can_edit": lambda module_key: user_can_edit_module(module_key),
        "can_delete": lambda module_key: user_can_delete_module(module_key),
    }


# ===== STATUS DO BANCO DE DADOS =====
DB_STATUS = {
    "available": False,
    "error": None,
    "mode": "offline",
    "environment": "development"
}

# Verificar ambiente configurado para operação.
if APP_ENV == "production":
    DB_STATUS["environment"] = "production"
elif APP_ENV in {"homolog", "staging"}:
    DB_STATUS["environment"] = "homolog"
else:
    DB_STATUS["environment"] = "development"

logger.info(f"🌍 Ambiente: {DB_STATUS['environment']}")

# Inicializar banco de dados (com tolerância para desenvolvimento)
try:
    init_auth_db()
    init_tenant_db()
    migrate_legacy_database()
    seed_admin()
    seed_all_accounts_default_data()
    DB_STATUS["available"] = True
    DB_STATUS["mode"] = "online"
    logger.info("✅ Banco de dados conectado e inicializado")
except Exception as e:
    DB_STATUS["available"] = False
    DB_STATUS["error"] = str(e)
    DB_STATUS["mode"] = "offline"
    
    if os.environ.get("DATABASE_URL"):
        # Em produção, isso é crítico
        logger.error(f"❌ ERRO CRÍTICO no Render: {e}")
        logger.info("   Verifique a conexão com o PostgreSQL no Render")
    else:
        # Em desenvolvimento, isso é apenas aviso
        logger.warning(f"⚠️  Banco de dados não disponível no startup: {e}")
        logger.info("   💡 Para testar, configure DATABASE_URL no .env com PostgreSQL local")
        logger.info("   💡 Ou use 'python app.py' para modo limitado")


def get_auth_connection():
    return get_db_connection()


def get_current_account_id():
    return session.get("account_id")


def get_current_user_id():
    return session.get("user_id")


def get_current_user_role():
    return session.get("role")


def get_current_user_permissions():
    if not session.get("user_id") or not session.get("account_id"):
        return {}
    if get_current_user_role() == "owner":
        return {"__owner__": True}

    cached_permissions = session.get("module_permissions")
    if isinstance(cached_permissions, dict):
        return cached_permissions

    conn = None
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT module, can_view, can_edit, can_delete FROM user_permissions WHERE account_id = %s AND user_id = %s",
            (session.get("account_id"), session.get("user_id")),
        ).fetchall()
        permissions = {
            row["module"]: {
                "can_view": bool(row["can_view"]),
                "can_edit": bool(row["can_edit"]),
                "can_delete": bool(row["can_delete"]),
            }
            for row in rows
        }
        if not permissions:
            permissions = {"__legacy_full_access__": True}
        session["module_permissions"] = permissions
        return permissions
    except Exception as exc:
        logger.exception("Falha ao carregar permissões do usuário atual: %s", exc)
        fallback_permissions = {"__legacy_full_access__": True}
        session["module_permissions"] = fallback_permissions
        return fallback_permissions
    finally:
        if conn:
            conn.close()


def user_can_view_module(module_key):
    if get_current_user_role() == "owner":
        return True
    permissions = get_current_user_permissions()
    if permissions.get("__legacy_full_access__"):
        return True
    module_permissions = permissions.get(module_key) or {}
    return bool(module_permissions.get("can_view"))


def user_can_edit_module(module_key):
    if get_current_user_role() == "owner":
        return True
    permissions = get_current_user_permissions()
    if permissions.get("__legacy_full_access__"):
        return True
    module_permissions = permissions.get(module_key) or {}
    return bool(module_permissions.get("can_edit"))


def user_can_delete_module(module_key):
    if get_current_user_role() == "owner":
        return True
    permissions = get_current_user_permissions()
    if permissions.get("__legacy_full_access__"):
        return True
    module_permissions = permissions.get(module_key) or {}
    return bool(module_permissions.get("can_delete"))


def get_default_route_for_current_user():
    if get_current_user_role() == "owner":
        return url_for("dashboard")

    permissions = get_current_user_permissions()
    if permissions.get("__legacy_full_access__"):
        return url_for("dashboard")

    route_by_module = [
        ("dashboard", lambda: url_for("dashboard")),
        ("vendas", lambda: url_for("vendas")),
        ("financeiro", lambda: url_for("financeiro")),
        ("estoque", lambda: url_for("controle_estoque")),
        ("compras", lambda: url_for("estoque_entrada")),
        ("relatorios", lambda: url_for("relatorios")),
        ("cadastro", lambda: url_for("cadastro", entity="clientes")),
    ]
    for module_key, route_getter in route_by_module:
        if user_can_view_module(module_key):
            return route_getter()
    flash("Seu usuário dependente não possui menus liberados. Solicite acesso ao administrador.", "error")
    return url_for("logout")


def get_tenant_connection(account_id=None):
    return get_db_connection()


def require_owner_access():
    if get_current_user_role() != "owner":
        flash("Somente o usuário principal pode gerenciar usuários desta conta.", "error")
        return False
    return True


ENDPOINT_MODULE_MAP = {
    "dashboard": "dashboard",
    "vendas": "vendas",
    "financeiro": "financeiro",
    "relatorios": "relatorios",
    "controle_estoque": "estoque",
    "estoque_ajuste": "estoque",
    "estoque_entrada": "compras",
    "cadastro": "cadastro",
    "parametros": "parametros",
    "import_excel.importar_dados": "cadastro",
    "access.controle_acesso": "usuarios",
    "auditoria.auditoria": "auditoria",
}


def _resolve_module_for_request(endpoint_name):
    module_key = ENDPOINT_MODULE_MAP.get(endpoint_name)
    if endpoint_name == "cadastro":
        entity = ((request.view_args or {}).get("entity") or "").lower()
        if entity == "usuarios":
            module_key = "usuarios"
    return module_key


def _request_attempts_delete():
    if request.method == "DELETE":
        return True
    if request.form.get("delete_id"):
        return True
    action = (request.form.get("action") or "").strip().lower()
    if action in {"delete", "delete_entry", "delete_category", "remove", "remove_item", "excluir"}:
        return True
    return False


@app.before_request
def enforce_module_permissions():
    if not session.get("user"):
        return None
    if get_current_user_role() == "owner":
        return None

    endpoint = request.endpoint or ""
    if endpoint.startswith("static"):
        return None
    if endpoint in {"login", "logout", "set_language", "forgot_password", "criar_conta_principal"}:
        return None

    module_key = _resolve_module_for_request(endpoint)
    if not module_key:
        return None

    if not user_can_view_module(module_key):
        log_audit_event(
            "access_denied",
            {
                "module": module_key,
                "endpoint": endpoint,
                "reason": "missing_can_view_permission",
            },
        )
        flash("Você não tem permissão para acessar este menu.", "error")
        return redirect(get_default_route_for_current_user())

    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not user_can_edit_module(module_key):
        log_audit_event(
            "write_denied",
            {
                "module": module_key,
                "endpoint": endpoint,
                "reason": "missing_can_edit_permission",
                "method": request.method,
            },
        )
        flash(
            "Dados disponíveis somente para consulta. Em caso de necessidade de acesso, consulte o administrador da conta.",
            "error",
        )
        return redirect(request.referrer or get_default_route_for_current_user())

    if _request_attempts_delete() and not user_can_delete_module(module_key):
        log_audit_event(
            "delete_denied",
            {
                "module": module_key,
                "endpoint": endpoint,
                "reason": "missing_can_delete_permission",
                "method": request.method,
            },
        )
        flash(
            "Você não possui permissão para remover dados neste módulo. Consulte o administrador da conta.",
            "error",
        )
        return redirect(request.referrer or get_default_route_for_current_user())
    return None


SETTINGS_DEFAULTS = {
    "smtp_provider": "gmail",
    "send_sale_thank_you": "0",
    "send_stock_min_alert": "0",
    "send_birthday_email": "0",
    "birthday_email_subject": "Feliz aniversário!",
    "birthday_email_body": "Olá {name}, desejamos um feliz aniversário! Obrigado por ser nosso cliente.",
    "last_birthday_run_date": "",
    "notification_email": "",
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_username": "",
    "smtp_password": "",
    "smtp_from_email": "",
    "smtp_from_name": "Kdc Systems",
    "smtp_use_tls": "1",
    "card_credit_surcharge_enabled": "0",
    "card_credit_rate_1": "0",
    "card_credit_rate_2": "0",
    "card_credit_rate_3": "0",
    "card_credit_rate_4": "0",
    "card_credit_rate_5": "0",
    "card_credit_rate_6": "0",
    "card_credit_rate_7": "0",
    "card_credit_rate_8": "0",
    "card_credit_rate_9": "0",
    "card_credit_rate_10": "0",
    "card_credit_rate_11": "0",
    "card_credit_rate_12": "0",
    "card_debit_surcharge_enabled": "0",
    "card_debit_rate": "0",
    "allow_multi_payment_sale": "0",
    "pix_key_type": "",
    "pix_key_value": "",
    "pix_receiver_name": "",
    "pix_receiver_city": "SAO PAULO",
    "default_profit_margin": "100",
    "default_stock_min_percent": "20",
    "log_retention_days": "30",
}

SMTP_PROVIDER_PRESETS = {
    "gmail": {"host": "smtp.gmail.com", "port": "587", "use_tls": "1"},
    "outlook": {"host": "smtp.office365.com", "port": "587", "use_tls": "1"},
    "yahoo": {"host": "smtp.mail.yahoo.com", "port": "587", "use_tls": "1"},
    "custom": {"host": "", "port": "587", "use_tls": "1"},
}

DEFAULT_FINANCIAL_CATEGORIES = [
    ("Aluguel", "payable"),
    ("Energia", "payable"),
    ("Agua", "payable"),
    ("Internet", "payable"),
    ("Folha de pagamento", "payable"),
    ("Impostos", "payable"),
    ("Compras de mercadoria", "payable"),
    ("Servicos terceiros", "payable"),
    ("Vendas", "receivable"),
    ("Recebimentos diversos", "receivable"),
    ("Transferencias internas", "both"),
]


def _clamp_rate(raw):
    try:
        return f"{min(max(float(raw or 0), 0), 100):.2f}"
    except (ValueError, TypeError):
        return "0.00"


def _clamp_margin(raw, default="100"):
    try:
        return f"{min(max(float(raw if raw is not None and raw != '' else default), 0), 10000):.2f}"
    except (ValueError, TypeError):
        return f"{float(default):.2f}"


def _clamp_percent(raw, default="0"):
    try:
        value = float(raw if raw is not None and raw != "" else default)
        return f"{min(max(value, 0), 100):.2f}"
    except (ValueError, TypeError):
        return f"{float(default):.2f}"


def _safe_float(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _safe_int(raw, default=0):
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _normalize_conversion_factor(raw):
    value = _safe_float(raw, 1.0)
    return max(1, int(round(value)))


def _normalize_product_code(raw):
    code = (raw or "").strip()
    return code or None


def _build_unique_product_code(conn, account_id, raw_code, exclude_product_id=None):
    base_code = _normalize_product_code(raw_code)
    if not base_code:
        return None

    candidate = base_code
    counter = 2
    while True:
        if exclude_product_id:
            exists = conn.execute(
                "SELECT id FROM products WHERE account_id = %s AND product_code = %s AND id <> %s LIMIT 1",
                (account_id, candidate, exclude_product_id),
            ).fetchone()
        else:
            exists = conn.execute(
                "SELECT id FROM products WHERE account_id = %s AND product_code = %s LIMIT 1",
                (account_id, candidate),
            ).fetchone()
        if not exists:
            return candidate
        candidate = f"{base_code}-{counter}"
        counter += 1


def _to_sale_units(quantity, conversion_factor):
    return float(quantity or 0) * float(conversion_factor or 1)


def _movement_type_label_pt(movement_type):
    mapping = {
        "sale": "Venda",
        "entrada": "Entrada",
        "ajuste_entrada": "Ajuste de entrada",
        "ajuste_saida": "Ajuste de saída",
        "xml_import": "Importação XML",
    }
    return mapping.get((movement_type or "").strip().lower(), movement_type or "-")


def _ensure_default_financial_categories(conn, account_id):
    for name, kind in DEFAULT_FINANCIAL_CATEGORIES:
        conn.execute(
            "INSERT INTO financial_categories (account_id, name, kind) VALUES (%s, %s, %s) ON CONFLICT (account_id, name, kind) DO NOTHING",
            (account_id, name, kind),
        )


def _round_price_to_tenth(price):
    """
    Arredonda o preço para terminar em 0.
    Exemplo: 23.84 -> 23.90, 23.81 -> 23.80
    """
    if price <= 0:
        return 0.0
    # Divide por 0.10 (1/10), arredonda para cima, multiplica por 0.10
    return round(price / 0.10) * 0.10


def _calculate_selling_price(cost, profit_margin_percent):
    """
    Calcula o preço de venda baseado no custo e margem de lucro.
    Fórmula: preço_venda = custo * (1 + margem/100)
    """
    if cost <= 0:
        return 0.0
    margin_factor = (profit_margin_percent or 100) / 100.0
    selling_price = cost * (1 + margin_factor)
    return _round_price_to_tenth(selling_price)


def _calculate_profit_margin(cost, selling_price):
    """
    Calcula o percentual de margem de lucro.
    Fórmula: margem = ((preço_venda - custo) / custo) * 100
    """
    if cost <= 0:
        return 0.0
    margin_percent = ((selling_price - cost) / cost) * 100
    return round(margin_percent, 2)


def _to_bool(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _sanitize_pix_key(raw_key_type, raw_key_value):
    key_type = (raw_key_type or "").strip().lower()
    key_value = (raw_key_value or "").strip()
    if key_type not in {"cpf", "telefone", "email", "aleatoria"}:
        return "", ""
    return key_type, key_value


def _format_date_br(value):
    if not value:
        return "-"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    text = str(value)
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return f"{text[8:10]}/{text[5:7]}/{text[0:4]}"
    return text


def _parse_iso_date(text):
    if not text:
        return None
    raw = str(text).strip()[:10]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


FINANCIAL_SOURCE_LABELS = {
    "sale": "Venda",
    "purchase": "Compra",
    "purchase_order": "Compra",
    "recurring_expense": "Despesa recorrente",
    "recurrence": "Despesa recorrente",
    "partial_payment": "Pagamento parcial",
    "manual": "Lançamento manual",
    "xml_import": "Importação XML",
    "internal_adjustment": "Ajuste interno",
}


def _normalize_financial_source(raw_source):
    source = (raw_source or "manual").strip().lower()
    aliases = {
        "venda": "sale",
        "compra": "purchase",
        "despesa_recorrente": "recurring_expense",
        "recorrente": "recurring_expense",
        "pagamento_parcial": "partial_payment",
        "partial_payment": "partial_payment",
        "lancamento_manual": "manual",
        "manual": "manual",
        "importacao_xml": "xml_import",
        "xml": "xml_import",
        "ajuste_interno": "internal_adjustment",
    }
    source = aliases.get(source, source)
    if source not in FINANCIAL_SOURCE_LABELS:
        return "manual"
    return source


def _is_auto_financial_source(source):
    return _normalize_financial_source(source) in {"sale", "purchase", "purchase_order", "xml_import", "recurring_expense", "recurrence"}


def _effective_financial_status(status, due_date):
    normalized = (status or "pendente").strip().lower()
    if normalized == "pago":
        return "pago"
    due = _parse_iso_date(due_date)
    today = datetime.now().date()
    if due and due < today:
        return "vencido"
    return "pendente"


def _run_financial_recurring_generation(conn, account_id):
    recurring_rows = conn.execute(
        "SELECT id, entry_type, description, category_id, supplier_id, client_id, amount, due_date, recurrence_days, source_ref "
        "FROM financial_entries WHERE account_id = %s AND is_recurring = 1 AND status = 'pago'",
        (account_id,),
    ).fetchall()

    created_count = 0
    for row in recurring_rows:
        ref = row["source_ref"] if str(row.get("source_ref") or "").startswith("recurring:") else f"recurring:{row['id']}"
        recurrence_days = max(_safe_int(row["recurrence_days"], 30), 1)
        current_due = _parse_iso_date(row["due_date"])
        if not current_due:
            continue

        pending_next = conn.execute(
            "SELECT id FROM financial_entries WHERE account_id = %s AND source_ref = %s AND due_date > %s LIMIT 1",
            (account_id, ref, current_due.strftime("%Y-%m-%d")),
        ).fetchone()
        if pending_next:
            continue

        next_due = current_due + timedelta(days=recurrence_days)
        next_due_text = next_due.strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO financial_entries (account_id, entry_type, description, category_id, supplier_id, client_id, amount, due_date, status, is_recurring, recurrence_days, source, source_ref, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendente', 1, %s, 'recurring_expense', %s, %s)",
            (
                account_id,
                row["entry_type"],
                row["description"],
                row["category_id"],
                row["supplier_id"],
                row["client_id"],
                float(row["amount"] or 0),
                next_due_text,
                recurrence_days,
                ref,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        created_count += 1

    return created_count


def _financial_due_alert_snapshot(conn, account_id):
    today_text = datetime.now().strftime("%Y-%m-%d")
    soon_text = (datetime.now().date() + timedelta(days=3)).strftime("%Y-%m-%d")

    overdue = conn.execute(
        "SELECT COUNT(*) AS qty, COALESCE(SUM(amount), 0) AS total "
        "FROM financial_entries WHERE account_id = %s AND status <> 'pago' AND due_date < %s",
        (account_id, today_text),
    ).fetchone()
    due_soon = conn.execute(
        "SELECT COUNT(*) AS qty, COALESCE(SUM(amount), 0) AS total "
        "FROM financial_entries WHERE account_id = %s AND status <> 'pago' AND due_date BETWEEN %s AND %s",
        (account_id, today_text, soon_text),
    ).fetchone()

    return {
        "overdue_qty": int(overdue["qty"] or 0),
        "overdue_total": float(overdue["total"] or 0),
        "due_soon_qty": int(due_soon["qty"] or 0),
        "due_soon_total": float(due_soon["total"] or 0),
        "today": today_text,
    }


def _maybe_flash_financial_alerts(snapshot):
    alert_key = f"financial_alerts_{snapshot['today']}"
    if session.get(alert_key):
        return
    if snapshot["overdue_qty"] > 0:
        flash(
            f"Financeiro: {snapshot['overdue_qty']} título(s) vencido(s), total R$ {snapshot['overdue_total']:.2f}.",
            "error",
        )
    if snapshot["due_soon_qty"] > 0:
        flash(
            f"Financeiro: {snapshot['due_soon_qty']} título(s) vencem nos próximos 3 dias, total R$ {snapshot['due_soon_total']:.2f}.",
            "info",
        )
    session[alert_key] = True


def _send_financial_due_alert_email(conn, account_id, snapshot):
    today = snapshot.get("today") or datetime.now().strftime("%Y-%m-%d")
    if snapshot.get("overdue_qty", 0) <= 0 and snapshot.get("due_soon_qty", 0) <= 0:
        return

    already_sent = conn.execute(
        "SELECT setting_value FROM account_settings WHERE account_id = %s AND setting_key = %s",
        (account_id, "financial_due_alert_last_date"),
    ).fetchone()
    if already_sent and str(already_sent["setting_value"] or "") == today:
        return

    recipients = get_primary_notification_recipients(account_id)
    if not recipients:
        return

    top_overdue = conn.execute(
        "SELECT description, due_date, amount FROM financial_entries "
        "WHERE account_id = %s AND status <> 'pago' AND due_date < %s ORDER BY due_date ASC LIMIT 10",
        (account_id, today),
    ).fetchall()
    top_due_soon = conn.execute(
        "SELECT description, due_date, amount FROM financial_entries "
        "WHERE account_id = %s AND status <> 'pago' AND due_date BETWEEN %s AND %s "
        "ORDER BY due_date ASC LIMIT 10",
        (account_id, today, (datetime.now().date() + timedelta(days=3)).strftime("%Y-%m-%d")),
    ).fetchall()

    lines = [
        f"- Vencidos: {snapshot['overdue_qty']} | Total: R$ {snapshot['overdue_total']:.2f}",
        f"- Vencendo em 3 dias: {snapshot['due_soon_qty']} | Total: R$ {snapshot['due_soon_total']:.2f}",
        "",
        "Detalhes vencidos:",
    ]
    if top_overdue:
        lines.extend([f"  • {r['due_date']} | {r['description']} | R$ {float(r['amount'] or 0):.2f}" for r in top_overdue])
    else:
        lines.append("  • Nenhum")

    lines.append("")
    lines.append("Detalhes próximos do vencimento:")
    if top_due_soon:
        lines.extend([f"  • {r['due_date']} | {r['description']} | R$ {float(r['amount'] or 0):.2f}" for r in top_due_soon])
    else:
        lines.append("  • Nenhum")

    sent, _err = send_email_with_settings(
        account_id,
        recipients,
        f"Alerta financeiro diário - {today}",
        "\n".join(lines),
    )
    if not sent:
        return

    conn.execute(
        "INSERT INTO account_settings (account_id, setting_key, setting_value, updated_at) "
        "VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (account_id, setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = EXCLUDED.updated_at",
        (account_id, "financial_due_alert_last_date", today, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )


def _safe_money(raw, default=0.0):
    if raw is None:
        return default
    text = str(raw).strip().replace(".", "").replace(",", ".") if isinstance(raw, str) and "," in str(raw) else str(raw).strip().replace(",", ".")
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def _xml_local_name(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _xml_find_first_text(node, local_names):
    targets = set(local_names)
    for child in node.iter():
        if _xml_local_name(child.tag) in targets:
            text = (child.text or "").strip()
            if text:
                return text
    return ""


def _parse_nfe_xml(xml_bytes):
    root = ET.fromstring(xml_bytes)

    invoice_number = _xml_find_first_text(root, ["nNF"])
    issue_raw = _xml_find_first_text(root, ["dhEmi", "dEmi"])
    issue_date = issue_raw[:10] if issue_raw else datetime.now().strftime("%Y-%m-%d")
    issue_date_display = _format_date_br(issue_date)
    supplier_name = _xml_find_first_text(root, ["xNome"])
    supplier_cnpj = re.sub(r"\D", "", _xml_find_first_text(root, ["CNPJ"]))[:14]
    total_amount = _safe_money(_xml_find_first_text(root, ["vNF"]), 0)

    invoice_key = ""
    for node in root.iter():
        if _xml_local_name(node.tag) == "infNFe":
            invoice_key = (node.attrib.get("Id") or "").replace("NFe", "").strip()
            break

    items = []
    for det in root.iter():
        if _xml_local_name(det.tag) != "det":
            continue
        prod = None
        for child in det:
            if _xml_local_name(child.tag) == "prod":
                prod = child
                break
        if prod is None:
            continue
        code = _xml_find_first_text(prod, ["cProd"])
        name = _xml_find_first_text(prod, ["xProd"])
        quantity = _safe_money(_xml_find_first_text(prod, ["qCom"]), 0)
        unit_price = _safe_money(_xml_find_first_text(prod, ["vUnCom"]), 0)
        item_total = _safe_money(_xml_find_first_text(prod, ["vProd"]), quantity * unit_price)
        if not name:
            continue
        items.append(
            {
                "code": code,
                "name": name,
                "quantity": quantity,
                "unit_price": unit_price,
                "total": item_total,
            }
        )

    if total_amount <= 0:
        total_amount = sum(float(item["total"] or 0) for item in items)

    return {
        "invoice_key": invoice_key,
        "invoice_number": invoice_number,
        "issue_date": issue_date,
        "issue_date_display": issue_date_display,
        "supplier_name": supplier_name,
        "supplier_cnpj": supplier_cnpj,
        "total_amount": float(total_amount or 0),
        "items": items,
    }


def get_account_settings(account_id):
    conn = get_tenant_connection()
    rows = conn.execute(
        "SELECT setting_key, setting_value FROM account_settings WHERE account_id = %s",
        (account_id,),
    ).fetchall()
    conn.close()
    settings = dict(SETTINGS_DEFAULTS)
    for row in rows:
        settings[row["setting_key"]] = row["setting_value"] or ""
    return settings


def _sanitize_provider(raw_provider):
    provider = (raw_provider or "custom").strip().lower()
    return provider if provider in SMTP_PROVIDER_PRESETS else "custom"


def _humanize_email_error(error_text, settings=None):
    message = (error_text or "").strip()
    lowered = message.lower()
    provider = _sanitize_provider((settings or {}).get("smtp_provider") if settings else "")

    if "badcredentials" in lowered or "535" in lowered or "authentication" in lowered:
        provider_hint = "do provedor"
        if provider == "gmail":
            provider_hint = "do Gmail"
        elif provider == "outlook":
            provider_hint = "do Outlook/Microsoft 365"
        elif provider == "yahoo":
            provider_hint = "do Yahoo"
        return (
            f"Falha de autenticação no SMTP {provider_hint}. "
            "Verifique o e-mail de origem e gere uma senha de aplicativo no provedor. "
            "A senha normal da conta geralmente não funciona."
        )

    if "timed out" in lowered or "timeout" in lowered:
        return "Tempo de conexão esgotado com o servidor de e-mail. Verifique internet, servidor SMTP e porta configurada."

    if "name or service not known" in lowered or "getaddrinfo failed" in lowered:
        return "Servidor SMTP inválido ou indisponível. Revise o provedor selecionado e, se manual, confira o host SMTP."

    if "connection refused" in lowered:
        return "Conexão recusada pelo servidor SMTP. Verifique host, porta e se o uso de TLS está correto."

    if "sender address rejected" in lowered or "from address not verified" in lowered:
        return "O e-mail de origem foi recusado pelo provedor. Confirme se ele está autorizado na conta SMTP."

    return "Não foi possível enviar e-mail com as configurações atuais. Revise provedor, e-mail de origem e senha de aplicativo."


def save_account_settings(account_id, form_data):
    provider = _sanitize_provider(form_data.get("smtp_provider"))
    preset = SMTP_PROVIDER_PRESETS.get(provider, SMTP_PROVIDER_PRESETS["custom"])
    from_email = (form_data.get("smtp_from_email") or "").strip()

    custom_host = (form_data.get("smtp_host") or "").strip()
    custom_port = (form_data.get("smtp_port") or "").strip()
    smtp_host = custom_host if provider == "custom" else (custom_host or preset["host"])
    smtp_port = custom_port if provider == "custom" else (custom_port or preset["port"])

    custom_tls = "1" if form_data.get("smtp_use_tls") else "0"
    smtp_use_tls = custom_tls if provider == "custom" else preset["use_tls"]

    smtp_username = (form_data.get("smtp_username") or "").strip()
    if not smtp_username and provider != "custom":
        smtp_username = from_email

    keys = list(SETTINGS_DEFAULTS.keys())
    pix_key_type, pix_key_value = _sanitize_pix_key(form_data.get("pix_key_type"), form_data.get("pix_key_value"))

    values = {
        "smtp_provider": provider,
        "send_sale_thank_you": "1" if form_data.get("send_sale_thank_you") else "0",
        "send_stock_min_alert": "1" if form_data.get("send_stock_min_alert") else "0",
        "send_birthday_email": "1" if form_data.get("send_birthday_email") else "0",
        "birthday_email_subject": (form_data.get("birthday_email_subject") or "Feliz aniversário!").strip(),
        "birthday_email_body": (form_data.get("birthday_email_body") or "Olá {name}, desejamos um feliz aniversário! Obrigado por ser nosso cliente.").strip(),
        "last_birthday_run_date": form_data.get("last_birthday_run_date") or "",
        "notification_email": (form_data.get("notification_email") or "").strip(),
        "smtp_host": smtp_host,
        "smtp_port": smtp_port or "587",
        "smtp_username": smtp_username,
        "smtp_password": (form_data.get("smtp_password") or "").strip(),
        "smtp_from_email": from_email,
        "smtp_from_name": (form_data.get("smtp_from_name") or "Kdc Systems").strip(),
        "smtp_use_tls": smtp_use_tls,
        "card_credit_surcharge_enabled": "1" if form_data.get("card_credit_surcharge_enabled") else "0",
        "card_debit_surcharge_enabled": "1" if form_data.get("card_debit_surcharge_enabled") else "0",
        "card_debit_rate": _clamp_rate(form_data.get("card_debit_rate")),
        **{f"card_credit_rate_{i}": _clamp_rate(form_data.get(f"card_credit_rate_{i}")) for i in range(1, 13)},
        "allow_multi_payment_sale": "1" if form_data.get("allow_multi_payment_sale") else "0",
        "default_profit_margin": _clamp_margin(form_data.get("default_profit_margin"), "100"),
        "default_stock_min_percent": _clamp_percent(form_data.get("default_stock_min_percent"), "20"),
        "pix_key_type": pix_key_type,
        "pix_key_value": pix_key_value,
        "pix_receiver_name": (form_data.get("pix_receiver_name") or "").strip(),
        "pix_receiver_city": (form_data.get("pix_receiver_city") or "SAO PAULO").strip().upper(),
        "log_retention_days": str(max(1, min(3650, int(form_data.get("log_retention_days") or 30)))),
    }

    conn = get_tenant_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for key in keys:
        conn.execute(
            """
            INSERT INTO account_settings (account_id, setting_key, setting_value, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (account_id, setting_key)
            DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = EXCLUDED.updated_at
            """,
            (account_id, key, values[key], now),
        )
    conn.commit()
    conn.close()


def set_account_setting(account_id, key, value):
    conn = get_tenant_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO account_settings (account_id, setting_key, setting_value, updated_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (account_id, setting_key)
        DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = EXCLUDED.updated_at
        """,
        (account_id, key, value, now),
    )
    conn.commit()
    conn.close()


def send_email_with_settings(account_id, recipients, subject, body):
    recipients = [email for email in recipients if email]
    if not recipients:
        return False, "Sem destinatário configurado"

    settings = get_account_settings(account_id)
    provider = _sanitize_provider(settings.get("smtp_provider"))
    preset = SMTP_PROVIDER_PRESETS.get(provider, SMTP_PROVIDER_PRESETS["custom"])
    host = settings.get("smtp_host") or preset["host"] or os.environ.get("SMTP_HOST", "")
    port = int(settings.get("smtp_port") or preset["port"] or os.environ.get("SMTP_PORT", 587))
    username = settings.get("smtp_username") or os.environ.get("SMTP_USERNAME", "")
    password = settings.get("smtp_password") or os.environ.get("SMTP_PASSWORD", "")
    from_email = settings.get("smtp_from_email") or os.environ.get("SMTP_FROM_EMAIL", "")
    from_name = settings.get("smtp_from_name") or "Kdc Systems"
    use_tls = _to_bool(settings.get("smtp_use_tls", preset["use_tls"]))

    if not username and provider != "custom":
        username = from_email

    if not host or not from_email:
        return False, "SMTP não configurado em Parâmetros"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            if use_tls:
                server.starttls()
            if username:
                server.login(username, password)
            server.send_message(msg)
        return True, "E-mail enviado com sucesso"
    except Exception as exc:
        logger.error("Falha ao enviar e-mail: %s", exc)
        return False, _humanize_email_error(str(exc), settings)


def run_daily_birthday_automation(account_id):
    settings = get_account_settings(account_id)
    if not _to_bool(settings.get("send_birthday_email")):
        return

    today = datetime.now().strftime("%Y-%m-%d")
    if settings.get("last_birthday_run_date") == today:
        return

    conn = get_tenant_connection()
    day_month = datetime.now().strftime("%m-%d")
    clients = conn.execute(
        """
        SELECT id, name, email, birth_date
        FROM clients
        WHERE account_id = %s
          AND email IS NOT NULL
          AND birth_date IS NOT NULL
          AND SUBSTRING(birth_date, 6, 5) = %s
        """,
        (account_id, day_month),
    ).fetchall()
    conn.close()

    subject_template = settings.get("birthday_email_subject") or "Feliz aniversário!"
    body_template = settings.get("birthday_email_body") or "Olá {name}, desejamos um feliz aniversário! Obrigado por ser nosso cliente."

    for client in clients:
        subject = subject_template.replace("{name}", client["name"] or "cliente")
        body = body_template.replace("{name}", client["name"] or "cliente")
        send_email_with_settings(account_id, [client["email"]], subject, body)

    set_account_setting(account_id, "last_birthday_run_date", today)


def get_primary_notification_recipients(account_id):
    settings = get_account_settings(account_id)
    recipients = []

    notification_email = (settings.get("notification_email") or "").strip()
    if notification_email:
        recipients.append(notification_email)

    auth_conn = get_auth_connection()
    owner = auth_conn.execute(
        "SELECT email FROM users WHERE account_id = %s AND role = 'owner' LIMIT 1",
        (account_id,),
    ).fetchone()
    auth_conn.close()

    owner_email = (owner.get("email") if owner else "") or ""
    owner_email = owner_email.strip()
    if owner_email and owner_email not in recipients:
        recipients.append(owner_email)

    return recipients


@app.route("/set_language/<lang_code>")
def set_language(lang_code):
    if lang_code in LANGUAGES:
        session["lang"] = lang_code
    fallback = get_default_route_for_current_user() if session.get("user") else url_for("dashboard")
    return redirect(request.referrer or fallback)


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(get_default_route_for_current_user())
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = authenticate_user(username, password)
        if user:
            session["user"] = user["username"]
            session["user_id"] = user["id"]
            session["user_name"] = user["name"] or user["username"]
            session["account_id"] = user["account_id"]
            session["account_name"] = user["account_name"]
            session["role"] = user["role"]
            session.pop("module_permissions", None)
            if user["role"] != "owner":
                get_current_user_permissions()
            return redirect(get_default_route_for_current_user())
        flash(translate("invalid_login"), "error")
    return render_template("login.html", title=translate("login_title"), hide_page_title=True)


@app.route("/criar-conta", methods=["POST"])
def criar_conta_principal():
    account_name = (request.form.get("account_name") or "").strip()
    owner_name = (request.form.get("owner_name") or "").strip()
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    email = (request.form.get("email") or "").strip() or None

    if not all([account_name, owner_name, username, password]):
        flash("Preencha empresa, responsável, usuário e senha para criar a conta principal.", "error")
        return redirect(url_for("login"))

    if " " in username:
        flash("O login da conta principal não pode conter espaços.", "error")
        return redirect(url_for("login"))

    try:
        create_account_with_owner(account_name, owner_name, username, password, email)
        flash("Conta principal criada com sucesso. Agora faça o login.", "success")
    except psycopg.IntegrityError:
        flash("Este login já está em uso. Escolha outro usuário principal.", "error")

    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect(url_for("login"))

    if not get_current_account_id():
        session.clear()
        flash("Sessão inválida. Faça login novamente.", "error")
        return redirect(url_for("login"))

    total_clients = 0
    total_products = 0
    total_sales = 0
    revenue_total = 0.0
    expenses_total = 0.0
    estimated_profit = 0.0
    low_stock_count = 0
    payable_open_total = 0.0
    overdue_payables_count = 0
    receivable_open_total = 0.0
    pending_receivables_count = 0
    period_key = "last_30_days"
    period_label = "Ultimos 30 dias"
    chart_points = []
    dashboard_alerts = []
    dashboard_kpis = []
    conn = None

    try:
        account_id = get_current_account_id()
        conn = get_tenant_connection()

        now_dt = datetime.now()
        today = now_dt.strftime("%Y-%m-%d")
        period_key = (request.args.get("period") or "last_30_days").strip().lower()

        if period_key == "today":
            start_date = today
            end_date = today
            period_label = "Hoje"
        elif period_key == "last_7_days":
            start_date = (now_dt - timedelta(days=6)).strftime("%Y-%m-%d")
            end_date = today
            period_label = "Ultimos 7 dias"
        elif period_key == "this_month":
            start_date = now_dt.replace(day=1).strftime("%Y-%m-%d")
            end_date = today
            period_label = "Este mes"
        else:
            period_key = "last_30_days"
            start_date = (now_dt - timedelta(days=29)).strftime("%Y-%m-%d")
            end_date = today
            period_label = "Ultimos 30 dias"

        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")
        range_days = max(1, (dt_end - dt_start).days + 1)
        prev_end_dt = dt_start - timedelta(days=1)
        prev_start_dt = prev_end_dt - timedelta(days=range_days - 1)
        prev_start_date = prev_start_dt.strftime("%Y-%m-%d")
        prev_end_date = prev_end_dt.strftime("%Y-%m-%d")

        def _percent_change(current_value, previous_value):
            current_value = float(current_value or 0)
            previous_value = float(previous_value or 0)
            if previous_value:
                return ((current_value - previous_value) / abs(previous_value)) * 100
            if current_value:
                return 100.0
            return 0.0

        def _currency_br(value):
            return f"R$ {float(value or 0):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

        total_clients = conn.execute("SELECT COUNT(*) FROM clients WHERE account_id = %s", (account_id,)).fetchone()[0]
        total_products = conn.execute("SELECT COUNT(*) FROM products WHERE account_id = %s", (account_id,)).fetchone()[0]
        total_sales = conn.execute("SELECT COUNT(*) FROM sales WHERE account_id = %s", (account_id,)).fetchone()[0]

        sales_current = conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS total FROM sales "
            "WHERE account_id = %s AND SUBSTRING(date, 1, 10) BETWEEN %s AND %s",
            (account_id, start_date, end_date),
        ).fetchone()
        sales_previous = conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS total FROM sales "
            "WHERE account_id = %s AND SUBSTRING(date, 1, 10) BETWEEN %s AND %s",
            (account_id, prev_start_date, prev_end_date),
        ).fetchone()

        expenses_current = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM financial_entries "
            "WHERE account_id = %s AND entry_type = 'payable' AND status = 'pago' AND due_date BETWEEN %s AND %s",
            (account_id, start_date, end_date),
        ).fetchone()
        expenses_previous = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM financial_entries "
            "WHERE account_id = %s AND entry_type = 'payable' AND status = 'pago' AND due_date BETWEEN %s AND %s",
            (account_id, prev_start_date, prev_end_date),
        ).fetchone()

        revenue_total = float(sales_current["total"] or 0)
        previous_revenue_total = float(sales_previous["total"] or 0)
        expenses_total = float(expenses_current["total"] or 0)
        previous_expenses_total = float(expenses_previous["total"] or 0)
        estimated_profit = revenue_total - expenses_total
        previous_estimated_profit = previous_revenue_total - previous_expenses_total

        revenue_change_pct = _percent_change(revenue_total, previous_revenue_total)
        expenses_change_pct = _percent_change(expenses_total, previous_expenses_total)
        profit_change_pct = _percent_change(estimated_profit, previous_estimated_profit)

        low_stock_row = conn.execute(
            "SELECT COUNT(*) AS qty FROM products WHERE account_id = %s AND COALESCE(stock_min, 0) > 0 AND COALESCE(stock, 0) <= stock_min",
            (account_id,),
        ).fetchone()
        low_stock_count = int(low_stock_row["qty"] or 0)

        stock_alert_rows = conn.execute(
            "SELECT name, stock, stock_min FROM products "
            "WHERE account_id = %s AND COALESCE(stock_min, 0) > 0 AND COALESCE(stock, 0) <= stock_min "
            "ORDER BY stock ASC, name ASC LIMIT 4",
            (account_id,),
        ).fetchall()

        payable_snapshot = conn.execute(
            "SELECT "
            "COALESCE(SUM(CASE WHEN status <> 'pago' THEN amount ELSE 0 END), 0) AS open_total, "
            "COALESCE(COUNT(CASE WHEN status <> 'pago' AND due_date < %s THEN 1 END), 0) AS overdue_count "
            "FROM financial_entries WHERE account_id = %s AND entry_type = 'payable'",
            (today, account_id),
        ).fetchone()
        receivable_snapshot = conn.execute(
            "SELECT "
            "COALESCE(SUM(CASE WHEN status <> 'pago' THEN amount ELSE 0 END), 0) AS open_total, "
            "COALESCE(COUNT(CASE WHEN status <> 'pago' THEN 1 END), 0) AS pending_count "
            "FROM financial_entries WHERE account_id = %s AND entry_type = 'receivable'",
            (account_id,),
        ).fetchone()

        payable_open_total = float(payable_snapshot["open_total"] or 0)
        overdue_payables_count = int(payable_snapshot["overdue_count"] or 0)
        receivable_open_total = float(receivable_snapshot["open_total"] or 0)
        pending_receivables_count = int(receivable_snapshot["pending_count"] or 0)

        sales_rows = conn.execute(
            "SELECT SUBSTRING(date, 1, 10) AS day, COALESCE(SUM(total), 0) AS total "
            "FROM sales WHERE account_id = %s AND SUBSTRING(date, 1, 10) BETWEEN %s AND %s "
            "GROUP BY SUBSTRING(date, 1, 10)",
            (account_id, start_date, end_date),
        ).fetchall()
        expense_rows = conn.execute(
            "SELECT due_date AS day, COALESCE(SUM(amount), 0) AS total "
            "FROM financial_entries WHERE account_id = %s AND entry_type = 'payable' AND status = 'pago' AND due_date BETWEEN %s AND %s "
            "GROUP BY due_date",
            (account_id, start_date, end_date),
        ).fetchall()

        sales_map = {str(row["day"]): float(row["total"] or 0) for row in sales_rows}
        expense_map = {str(row["day"]): float(row["total"] or 0) for row in expense_rows}

        cursor_dt = dt_start
        while cursor_dt <= dt_end:
            day = cursor_dt.strftime("%Y-%m-%d")
            revenue_value = sales_map.get(day, 0.0)
            expense_value = expense_map.get(day, 0.0)
            chart_points.append(
                {
                    "day": day,
                    "label": _format_date_br(day),
                    "revenue": revenue_value,
                    "expenses": expense_value,
                    "profit": revenue_value - expense_value,
                }
            )
            cursor_dt += timedelta(days=1)

        if overdue_payables_count > 0:
            dashboard_alerts.append(
                {
                    "tone": "critical",
                    "icon": "!",
                    "title": f"{overdue_payables_count} contas vencidas",
                    "message": "Regularize pagamentos para evitar juros e impacto no caixa.",
                    "href": url_for("financeiro") + "#a-pagar",
                }
            )

        if low_stock_count > 0:
            highlighted_products = ", ".join([str(row["name"]) for row in stock_alert_rows[:3]])
            dashboard_alerts.append(
                {
                    "tone": "warning",
                    "icon": "[]",
                    "title": f"{low_stock_count} produtos com estoque baixo",
                    "message": (highlighted_products + ".") if highlighted_products else "Reabasteca os itens com estoque critico.",
                    "href": url_for("controle_estoque"),
                }
            )

        if revenue_total < previous_revenue_total:
            drop_pct = abs(_percent_change(revenue_total, previous_revenue_total))
            dashboard_alerts.append(
                {
                    "tone": "info",
                    "icon": "↓",
                    "title": "Queda nas vendas",
                    "message": f"Faturamento caiu {drop_pct:.1f}% em relacao ao periodo anterior.",
                    "href": url_for("vendas"),
                }
            )

        if not dashboard_alerts:
            dashboard_alerts.append(
                {
                    "tone": "positive",
                    "icon": "+",
                    "title": "Operacao sob controle",
                    "message": "Sem alertas criticos no periodo selecionado.",
                    "href": url_for("dashboard", period=period_key),
                }
            )

        dashboard_kpis = [
            {
                "title": "Faturamento",
                "value": _currency_br(revenue_total),
                "delta": revenue_change_pct,
                "delta_prefix": "vs periodo anterior",
                "card_tone": "success",
                "icon": "↗",
                "static_badge": False,
                "invert_delta": False,
            },
            {
                "title": "Despesas",
                "value": _currency_br(expenses_total),
                "delta": expenses_change_pct,
                "delta_prefix": "vs periodo anterior",
                "card_tone": "danger",
                "icon": "↘",
                "static_badge": False,
                "invert_delta": True,
            },
            {
                "title": "Lucro estimado",
                "value": _currency_br(estimated_profit),
                "delta": profit_change_pct,
                "delta_prefix": "vs periodo anterior",
                "card_tone": "primary",
                "icon": "≈",
                "static_badge": False,
                "invert_delta": False,
            },
            {
                "title": "Estoque critico",
                "value": f"{low_stock_count} itens",
                "delta": 0,
                "delta_prefix": "reposicao necessaria",
                "card_tone": "warning",
                "icon": "!",
                "static_badge": True,
                "invert_delta": False,
            },
        ]
    except Exception as exc:
        logger.exception("Falha ao carregar dashboard: %s", exc)
        flash("Houve um problema ao carregar o painel. Exibindo dados parciais.", "error")
    finally:
        if conn:
            conn.close()
    
    try:
        return render_template(
            "dashboard.html",
            title=translate("dashboard_title"),
            user=session.get("user_name") or session.get("user"),
            welcome_text=translate("dashboard_welcome_text"),
            total_clients=total_clients,
            total_products=total_products,
            total_sales=total_sales,
            period_key=period_key,
            period_label=period_label,
            dashboard_kpis=dashboard_kpis,
            chart_points=chart_points,
            revenue_total=revenue_total,
            expenses_total=expenses_total,
            estimated_profit=estimated_profit,
            low_stock_count=low_stock_count,
            payable_open_total=payable_open_total,
            overdue_payables_count=overdue_payables_count,
            receivable_open_total=receivable_open_total,
            pending_receivables_count=pending_receivables_count,
            dashboard_alerts=dashboard_alerts,
        )
    except Exception as exc:
        logger.exception("Falha ao renderizar dashboard: %s", exc)
        flash("Houve uma falha ao abrir o Dashboard. Exibindo modo seguro.", "error")
        return render_template("placeholder.html", title=translate("dashboard_title"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    """Página para recuperação de senha - admin reseta manualmente"""
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        
        if username and email:
            conn = get_auth_connection()
            user = conn.execute(
                "SELECT id, name FROM users WHERE username = %s AND email = %s",
                (username, email)
            ).fetchone()
            conn.close()
            
            if user:
                flash(
                    f"Usuário '{username}' encontrado. Entre em contato com o administrador para resetar sua senha.",
                    "info"
                )
                return redirect(url_for("login"))
            else:
                flash("Usuário ou e-mail não encontrados", "error")
        else:
            flash("Preencha todos os campos", "error")
    
    return render_template(
        "forgot_password.html", 
        title="Recuperar Senha"
    )


def get_entity_title(entity):
    labels = {
        "usuarios": translate("menu_users"),
        "produtos": translate("menu_products"),
        "clientes": translate("menu_clients"),
        "fornecedores": translate("menu_suppliers"),
        "categorias": translate("category_label"),
        "unidades": translate("unit_label"),
    }
    return f"Cadastro de {labels.get(entity, entity.capitalize())}"


@app.route("/parametros", methods=["GET", "POST"])
def parametros():
    if not session.get("user"):
        return redirect(url_for("login"))
    if not user_can_view_module("parametros"):
        flash("Você não tem permissão para acessar este menu.", "error")
        return redirect(url_for("dashboard"))

    account_id = get_current_account_id()
    read_only = not user_can_edit_module("parametros")
    if request.method == "POST":
        if read_only:
            flash(
                "Dados disponíveis somente para consulta. Em caso de necessidade de acesso, consulte o administrador da conta.",
                "error",
            )
            return redirect(url_for("parametros"))
        if request.form.get("action") == "test_smtp":
            test_email = (request.form.get("test_email") or "").strip()
            recipients = [test_email] if test_email else get_primary_notification_recipients(account_id)
            if not recipients:
                flash("Informe um e-mail de teste ou preencha o e-mail de destino principal.", "error")
                return redirect(url_for("parametros"))
            sent, err = send_email_with_settings(
                account_id,
                recipients,
                "Teste SMTP - Kdc Systems",
                "Este é um e-mail de teste enviado pela tela de parâmetros.",
            )
            if sent:
                flash(f"Teste SMTP enviado para: {', '.join(recipients)}.", "success")
            else:
                flash(f"Falha no teste SMTP: {err}", "error")
            return redirect(url_for("parametros"))

        save_account_settings(account_id, request.form)
        flash("Parâmetros atualizados com sucesso.", "success")
        return redirect(url_for("parametros"))

    settings = get_account_settings(account_id)
    return render_template("parametros.html", title="Parâmetros", settings=settings, read_only=read_only)


@app.route("/cadastro/<entity>", methods=["GET", "POST"])
def cadastro(entity):
    if not session.get("user"):
        return redirect(url_for("login"))

    entity = entity.lower()
    if entity == "usuarios" and not user_can_view_module("usuarios"):
        flash("Você não tem permissão para acessar este menu.", "error")
        return redirect(url_for("dashboard"))

    conn = get_auth_connection() if entity == "usuarios" else get_tenant_connection()
    account_id = get_current_account_id()
    current_user_id = get_current_user_id()
    rows = []
    categories = conn.execute("SELECT * FROM categories WHERE account_id = %s ORDER BY name", (account_id,)).fetchall() if entity != "usuarios" else []
    units = conn.execute("SELECT * FROM units WHERE account_id = %s ORDER BY name", (account_id,)).fetchall() if entity != "usuarios" else []
    suppliers = conn.execute("SELECT * FROM suppliers WHERE account_id = %s ORDER BY name", (account_id,)).fetchall() if entity != "usuarios" else []
    account_settings = get_account_settings(account_id) if entity == "produtos" else {}
    default_profit_margin = account_settings.get("default_profit_margin", "100") if entity == "produtos" else "100"
    default_stock_min_percent = account_settings.get("default_stock_min_percent", "20") if entity == "produtos" else "20"
    edit_id = request.args.get("edit_id") or request.form.get("edit_id")
    edit_data = None

    if edit_id:
        if entity == "usuarios":
            edit_data = dict(conn.execute("SELECT * FROM users WHERE id = %s AND account_id = %s", (edit_id, account_id)).fetchone() or {})
        elif entity == "produtos":
            edit_data = dict(conn.execute("SELECT * FROM products WHERE id = %s AND account_id = %s", (edit_id, account_id)).fetchone() or {})
            if edit_data.get("expiration_date"):
                edit_data["expiration_date"] = normalize_date_for_input(edit_data.get("expiration_date"))
        elif entity == "clientes":
            edit_data = dict(conn.execute("SELECT * FROM clients WHERE id = %s AND account_id = %s", (edit_id, account_id)).fetchone() or {})
        elif entity == "fornecedores":
            edit_data = dict(conn.execute("SELECT * FROM suppliers WHERE id = %s AND account_id = %s", (edit_id, account_id)).fetchone() or {})
        elif entity == "categorias":
            edit_data = dict(conn.execute("SELECT * FROM categories WHERE id = %s AND account_id = %s", (edit_id, account_id)).fetchone() or {})
        elif entity == "unidades":
            edit_data = dict(conn.execute("SELECT * FROM units WHERE id = %s AND account_id = %s", (edit_id, account_id)).fetchone() or {})

    if request.method == "POST":
        try:
            if request.form.get("delete_id"):
                delete_id = request.form.get("delete_id")
                if entity == "usuarios":
                    conn.execute("DELETE FROM users WHERE id = %s AND account_id = %s AND role != 'owner'", (delete_id, account_id))
                    conn.commit()
                    flash("Registro deletado com sucesso", "success")
                elif entity == "produtos":
                    conn.execute("DELETE FROM products WHERE id = %s AND account_id = %s", (delete_id, account_id))
                    conn.commit()
                    flash("Registro deletado com sucesso", "success")
                elif entity == "clientes":
                    conn.execute("DELETE FROM clients WHERE id = %s AND account_id = %s", (delete_id, account_id))
                    conn.commit()
                    flash("Registro deletado com sucesso", "success")
                elif entity == "fornecedores":
                    conn.execute("DELETE FROM suppliers WHERE id = %s AND account_id = %s", (delete_id, account_id))
                    conn.commit()
                    flash("Registro deletado com sucesso", "success")
                elif entity == "categorias":
                    used_in_products = conn.execute("SELECT COUNT(*) FROM products WHERE category_id = %s AND account_id = %s", (delete_id, account_id)).fetchone()[0]
                    used_in_suppliers = conn.execute("SELECT COUNT(*) FROM suppliers WHERE category_id = %s AND account_id = %s", (delete_id, account_id)).fetchone()[0]
                    if used_in_products > 0 or used_in_suppliers > 0:
                        flash("Não é possível deletar esta categoria pois está sendo usada", "error")
                    else:
                        conn.execute("DELETE FROM categories WHERE id = %s AND account_id = %s", (delete_id, account_id))
                        conn.commit()
                        flash("Registro deletado com sucesso", "success")
                elif entity == "unidades":
                    used_in_products = conn.execute("SELECT COUNT(*) FROM products WHERE unit_id = %s AND account_id = %s", (delete_id, account_id)).fetchone()[0]
                    if used_in_products > 0:
                        flash("Não é possível deletar esta unidade pois está sendo usada", "error")
                    else:
                        conn.execute("DELETE FROM units WHERE id = %s AND account_id = %s", (delete_id, account_id))
                        conn.commit()
                        flash("Registro deletado com sucesso", "success")
                conn.close()
                return redirect(url_for("cadastro", entity=entity))

            if entity == "usuarios" and request.form.get("action") == "reset":
                reset_id = request.form.get("reset_id")
                reset_password = request.form.get("reset_password")
                if reset_id and reset_password:
                    conn.execute("UPDATE users SET password = %s WHERE id = %s AND account_id = %s", (reset_password, reset_id, account_id))
                    conn.commit()
                    flash(translate("record_saved"), "success")

            elif entity == "usuarios":
                name = request.form.get("name")
                username = request.form.get("username")
                password = request.form.get("password")
                email = request.form.get("email")
                edit_id_form = request.form.get("edit_id")

                if not (name and username):
                    flash("Nome e Login são obrigatórios", "error")
                elif " " in username:
                    flash("Login não pode conter espaços", "error")
                else:
                    try:
                        if edit_id_form:
                            if password:
                                conn.execute(
                                    "UPDATE users SET name = %s, password = %s, email = %s WHERE id = %s AND account_id = %s",
                                    (name, password, email, edit_id_form, account_id),
                                )
                            else:
                                conn.execute(
                                    "UPDATE users SET name = %s, email = %s WHERE id = %s AND account_id = %s",
                                    (name, email, edit_id_form, account_id),
                                )
                        else:
                            if not password:
                                flash("Senha é obrigatória para novo usuário", "error")
                            else:
                                conn.execute(
                                    "INSERT INTO users (account_id, name, username, password, email, role, parent_user_id, is_admin, created_at) VALUES (%s, %s, %s, %s, %s, 'operator', %s, 0, %s)",
                                    (account_id, name, username, password, email, current_user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                )
                        conn.commit()
                        flash(translate("record_saved"), "success")
                        conn.close()
                        return redirect(url_for("cadastro", entity=entity))
                    except psycopg.IntegrityError:
                        conn.rollback()
                        flash("Este login já existe", "error")

            elif entity == "produtos":
                new_category_name = request.form.get("new_category_name")
                new_unit_name = request.form.get("new_unit_name")
                if new_category_name:
                    new_category_id = None
                    try:
                        new_category_id = conn.execute(
                            "INSERT INTO categories (account_id, name) VALUES (%s, %s) RETURNING id",
                            (account_id, new_category_name.strip()),
                        ).fetchone()[0]
                        conn.commit()
                        flash(translate("record_saved"), "success")
                    except psycopg.IntegrityError:
                        conn.rollback()
                        flash("Esta categoria já existe", "error")
                    categories = conn.execute("SELECT * FROM categories WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
                    units = conn.execute("SELECT * FROM units WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
                    suppliers = conn.execute("SELECT * FROM suppliers WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
                    edit_data = dict(request.form)
                    if new_category_id is not None:
                        edit_data["category_id"] = str(new_category_id)
                elif new_unit_name:
                    new_unit_id = None
                    try:
                        new_unit_id = conn.execute(
                            "INSERT INTO units (account_id, name) VALUES (%s, %s) RETURNING id",
                            (account_id, new_unit_name.strip()),
                        ).fetchone()[0]
                        conn.commit()
                        flash(translate("record_saved"), "success")
                    except psycopg.IntegrityError:
                        conn.rollback()
                        flash("Esta unidade já existe", "error")
                    categories = conn.execute("SELECT * FROM categories WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
                    units = conn.execute("SELECT * FROM units WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
                    suppliers = conn.execute("SELECT * FROM suppliers WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
                    edit_data = dict(request.form)
                    if new_unit_id is not None:
                        edit_data["unit_id"] = str(new_unit_id)

                else:
                    name = request.form.get("name")
                    product_code = _normalize_product_code(request.form.get("product_code"))
                    category_id = request.form.get("category_id")
                    unit_id = request.form.get("unit_id")
                    supplier_id = request.form.get("supplier_id") or None
                    cost = float(request.form.get("cost") or 0)
                    price = float(request.form.get("price") or 0)
                    stock = int(request.form.get("stock") or 0)
                    stock_min = int(request.form.get("stock_min") or 0)
                    expiration_date = request.form.get("expiration_date") or None
                    edit_id_form = request.form.get("edit_id")

                    if name and category_id and unit_id:
                        # Calcular margem de lucro
                        margin_percent = _safe_float(request.form.get("margin_percent"), None)
                        settings = get_account_settings(account_id)
                        default_margin = _safe_float(settings.get("default_profit_margin", "100"))
                        default_stock_percent = _safe_float(settings.get("default_stock_min_percent", "20"))
                        if margin_percent is None:
                            margin_percent = default_margin
                        if cost > 0 and price == 0:
                            price = _calculate_selling_price(cost, margin_percent)
                        elif cost > 0 and price > 0:
                            margin_percent = _calculate_profit_margin(cost, price)

                        if stock > 0 and stock_min <= 0:
                            stock_min = max(0, int(round(stock * (default_stock_percent / 100))))

                        # Unidade de compra e fator de conversao
                        unit_buy = (request.form.get("unit_buy") or "").strip() or None
                        conversion_factor = _normalize_conversion_factor(request.form.get("conversion_factor"))
                        status = (request.form.get("status") or "ativo").strip().lower()
                        if status not in {"ativo", "inativo"}:
                            status = "ativo"

                        if product_code:
                            if edit_id_form:
                                duplicate = conn.execute(
                                    "SELECT id FROM products WHERE account_id = %s AND product_code = %s AND id <> %s LIMIT 1",
                                    (account_id, product_code, edit_id_form),
                                ).fetchone()
                            else:
                                duplicate = conn.execute(
                                    "SELECT id FROM products WHERE account_id = %s AND product_code = %s LIMIT 1",
                                    (account_id, product_code),
                                ).fetchone()
                            if duplicate:
                                edit_data = dict(request.form)
                                flash("Código do produto já está em uso. Use outro código.", "error")
                                conn.close()
                                return render_template(
                                    "cadastro.html",
                                    title=get_entity_title(entity),
                                    entity=entity,
                                    rows=rows,
                                    categories=categories,
                                    units=units,
                                    suppliers=suppliers,
                                    default_profit_margin=default_profit_margin,
                                    default_stock_min_percent=default_stock_min_percent,
                                    edit_id=edit_id,
                                    edit_data=edit_data,
                                )

                        if edit_id_form:
                            conn.execute(
                                "UPDATE products SET name = %s, product_code = %s, category_id = %s, unit_id = %s, supplier_id = %s, cost = %s, price = %s, margin_percent = %s, unit_buy = %s, conversion_factor = %s, stock = %s, stock_min = %s, status = %s, expiration_date = %s WHERE id = %s AND account_id = %s",
                                (name, product_code, category_id, unit_id, supplier_id, cost, price, margin_percent, unit_buy, conversion_factor, stock, stock_min, status, expiration_date, edit_id_form, account_id),
                            )
                        else:
                            conn.execute(
                                "INSERT INTO products (account_id, name, product_code, category_id, unit_id, supplier_id, cost, price, margin_percent, unit_buy, conversion_factor, stock, stock_min, status, expiration_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (account_id, name, product_code, category_id, unit_id, supplier_id, cost, price, margin_percent, unit_buy, conversion_factor, stock, stock_min, status, expiration_date),
                            )
                        conn.commit()
                        flash(translate("record_saved"), "success")
                        conn.close()
                        return redirect(url_for("cadastro", entity=entity))
                    edit_data = dict(request.form)
                    flash("Preencha todos os campos obrigatórios", "error")

            elif entity == "clientes":
                name = request.form.get("name")
                cpf = re.sub(r"\D", "", request.form.get("cpf") or "")[:11]
                email = (request.form.get("email") or "").strip() or None
                phone = re.sub(r"\D", "", request.form.get("phone") or "")[:15] or None
                whatsapp = re.sub(r"\D", "", request.form.get("whatsapp") or "")[:15] or None
                birth_date = request.form.get("birth_date") or None
                notes = (request.form.get("notes") or "").strip() or None
                street = request.form.get("street")
                number = request.form.get("number")
                complement = request.form.get("complement")
                neighborhood = request.form.get("neighborhood")
                city = request.form.get("city")
                state = re.sub(r"[^A-Za-z]", "", request.form.get("state") or "").upper()[:2]
                country = request.form.get("country")
                postal_code = re.sub(r"\D", "", request.form.get("postal_code") or "")[:8]
                gender = (request.form.get("gender") or "nao_informar").strip()
                edit_id_form = request.form.get("edit_id")

                if gender not in {"masculino", "feminino", "nao_informar"}:
                    gender = "nao_informar"

                if name:
                    if edit_id_form:
                        conn.execute(
                            "UPDATE clients SET name = %s, cpf = %s, email = %s, phone = %s, whatsapp = %s, birth_date = %s, notes = %s, street = %s, number = %s, complement = %s, neighborhood = %s, city = %s, state = %s, country = %s, postal_code = %s, gender = %s WHERE id = %s AND account_id = %s",
                            (name, cpf, email, phone, whatsapp, birth_date, notes, street, number, complement, neighborhood, city, state, country, postal_code, gender, edit_id_form, account_id),
                        )
                    else:
                        conn.execute(
                            "INSERT INTO clients (account_id, name, cpf, email, phone, whatsapp, birth_date, notes, street, number, complement, neighborhood, city, state, country, postal_code, gender) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (account_id, name, cpf, email, phone, whatsapp, birth_date, notes, street, number, complement, neighborhood, city, state, country, postal_code, gender),
                        )
                    conn.commit()
                    flash(translate("record_saved"), "success")
                    conn.close()
                    return redirect(url_for("cadastro", entity=entity))
                edit_data = dict(request.form)
                flash("Nome é obrigatório", "error")

            elif entity == "fornecedores":
                new_category_name = request.form.get("new_category_name")
                if new_category_name:
                    new_category_id = None
                    try:
                        new_category_id = conn.execute(
                            "INSERT INTO categories (account_id, name) VALUES (%s, %s) RETURNING id",
                            (account_id, new_category_name.strip()),
                        ).fetchone()[0]
                        conn.commit()
                        flash(translate("record_saved"), "success")
                    except psycopg.IntegrityError:
                        conn.rollback()
                        flash("Esta categoria já existe", "error")
                    categories = conn.execute("SELECT * FROM categories WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
                    edit_data = dict(request.form)
                    if new_category_id is not None:
                        edit_data["category_id"] = str(new_category_id)

                else:
                    name = request.form.get("name")
                    cnpj = re.sub(r"\D", "", request.form.get("cnpj") or "")[:14]
                    email = (request.form.get("email") or "").strip() or None
                    phone = re.sub(r"\D", "", request.form.get("phone") or "")[:15] or None
                    whatsapp = re.sub(r"\D", "", request.form.get("whatsapp") or "")[:15] or None
                    notes = (request.form.get("notes") or "").strip() or None
                    street = request.form.get("street")
                    number = request.form.get("number")
                    complement = request.form.get("complement")
                    neighborhood = request.form.get("neighborhood")
                    city = request.form.get("city")
                    state = re.sub(r"[^A-Za-z]", "", request.form.get("state") or "").upper()[:2]
                    country = request.form.get("country")
                    postal_code = re.sub(r"\D", "", request.form.get("postal_code") or "")[:8]
                    category_id = request.form.get("category_id")
                    edit_id_form = request.form.get("edit_id")

                    if name and category_id:
                        if edit_id_form:
                            conn.execute(
                                "UPDATE suppliers SET name = %s, cnpj = %s, email = %s, phone = %s, whatsapp = %s, notes = %s, street = %s, number = %s, complement = %s, neighborhood = %s, city = %s, state = %s, country = %s, postal_code = %s, category_id = %s WHERE id = %s AND account_id = %s",
                                (name, cnpj, email, phone, whatsapp, notes, street, number, complement, neighborhood, city, state, country, postal_code, category_id, edit_id_form, account_id),
                            )
                        else:
                            conn.execute(
                                "INSERT INTO suppliers (account_id, name, cnpj, email, phone, whatsapp, notes, street, number, complement, neighborhood, city, state, country, postal_code, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (account_id, name, cnpj, email, phone, whatsapp, notes, street, number, complement, neighborhood, city, state, country, postal_code, category_id),
                            )
                        conn.commit()
                        flash(translate("record_saved"), "success")
                        conn.close()
                        return redirect(url_for("cadastro", entity=entity))
                    edit_data = dict(request.form)
                    flash("Nome e Categoria são obrigatórios", "error")

            elif entity == "categorias":
                name = request.form.get("name")
                edit_id_form = request.form.get("edit_id")
                if name:
                    try:
                        if edit_id_form:
                            conn.execute("UPDATE categories SET name = %s WHERE id = %s AND account_id = %s", (name, edit_id_form, account_id))
                        else:
                            conn.execute("INSERT INTO categories (account_id, name) VALUES (%s, %s)", (account_id, name))
                        conn.commit()
                        flash(translate("record_saved"), "success")
                        conn.close()
                        return redirect(url_for("cadastro", entity=entity))
                    except psycopg.IntegrityError:
                        conn.rollback()
                        flash("Esta categoria já existe", "error")
                else:
                    flash("Nome é obrigatório", "error")

            elif entity == "unidades":
                name = request.form.get("name")
                edit_id_form = request.form.get("edit_id")
                if name:
                    try:
                        if edit_id_form:
                            conn.execute("UPDATE units SET name = %s WHERE id = %s AND account_id = %s", (name, edit_id_form, account_id))
                        else:
                            conn.execute("INSERT INTO units (account_id, name) VALUES (%s, %s)", (account_id, name))
                        conn.commit()
                        flash(translate("record_saved"), "success")
                        conn.close()
                        return redirect(url_for("cadastro", entity=entity))
                    except psycopg.IntegrityError:
                        conn.rollback()
                        flash("Esta unidade já existe", "error")
                else:
                    flash("Nome é obrigatório", "error")

        except Exception as error:
            conn.rollback()
            logger.error(f"Erro ao processar cadastro: {error}")
            flash(translate("error_required_fields"), "error")

    if entity == "usuarios":
        rows = conn.execute("SELECT * FROM users WHERE account_id = %s ORDER BY CASE WHEN role = 'owner' THEN 0 ELSE 1 END, username", (account_id,)).fetchall()
    elif entity == "produtos":
        rows = conn.execute(
            "SELECT p.*, c.name AS category_name, u.name AS unit_name, s.name AS supplier_name "
            "FROM products p "
            "LEFT JOIN categories c ON p.category_id = c.id "
            "LEFT JOIN units u ON p.unit_id = u.id "
            "LEFT JOIN suppliers s ON p.supplier_id = s.id "
            "WHERE p.account_id = %s ORDER BY p.name",
            (account_id,),
        ).fetchall()
    elif entity == "clientes":
        rows = conn.execute("SELECT * FROM clients WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
        rows = [{**dict(r), "birth_date_display": _format_date_br(r.get("birth_date"))} for r in rows]
    elif entity == "fornecedores":
        rows = conn.execute(
            "SELECT s.*, c.name AS category_name FROM suppliers s LEFT JOIN categories c ON s.category_id = c.id WHERE s.account_id = %s ORDER BY s.name",
            (account_id,),
        ).fetchall()
    elif entity == "categorias":
        rows = conn.execute("SELECT * FROM categories WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
    elif entity == "unidades":
        rows = conn.execute("SELECT * FROM units WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
    else:
        conn.close()
        flash(translate("error_required_fields"), "error")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template(
        "cadastro.html",
        title=get_entity_title(entity),
        entity=entity,
        rows=rows,
        categories=categories,
        units=units,
        suppliers=suppliers,
        default_profit_margin=default_profit_margin,
        default_stock_min_percent=default_stock_min_percent,
        edit_id=edit_id,
        edit_data=edit_data,
    )


@app.route("/vendas", methods=["GET", "POST"])
def vendas():
    if not session.get("user"):
        return redirect(url_for("login"))
    account_id = get_current_account_id()
    conn = get_tenant_connection()
    products = conn.execute(
        "SELECT p.*, u.name AS unit_name "
        "FROM products p "
        "LEFT JOIN units u ON p.unit_id = u.id "
        "WHERE p.account_id = %s AND COALESCE(p.status, 'ativo') = 'ativo' "
        "ORDER BY (SELECT COALESCE(SUM(quantity), 0) FROM sale_items si WHERE si.product_id = p.id) DESC, p.name",
        (account_id,),
    ).fetchall()
    clients = conn.execute("SELECT * FROM clients WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
    pix_code = None
    cash_summary = None
    settings = get_account_settings(account_id)
    card_settings_json = json.dumps({
        "credit_enabled": settings.get("card_credit_surcharge_enabled") == "1",
        "debit_enabled": settings.get("card_debit_surcharge_enabled") == "1",
        "debit_rate": float(settings.get("card_debit_rate") or 0),
        "credit_rates": {str(i): float(settings.get(f"card_credit_rate_{i}") or 0) for i in range(1, 13)},
    })
    payment_ui_settings_json = json.dumps({
        "allow_multi": settings.get("allow_multi_payment_sale") == "1",
        "pix_key_type": settings.get("pix_key_type") or "",
        "pix_key_value": settings.get("pix_key_value") or "",
        "pix_receiver_name": settings.get("pix_receiver_name") or (session.get("account_name") or "KDC SYSTEMS"),
        "pix_receiver_city": settings.get("pix_receiver_city") or "SAO PAULO",
    })

    if request.method == "POST":
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")
        discount = _safe_float(request.form.get("discount") or 0)
        surcharge = _safe_float(request.form.get("surcharge") or 0)
        payment_method = request.form.get("payment_method") or "Dinheiro"
        payment_received = _safe_float(request.form.get("payment_received") or 0)
        installments_single = _safe_int(request.form.get("installments") or 1, 1)
        client_id = request.form.get("client_id") or None
        items = []
        total = 0
        cost_total = 0
        valid = True

        for pid, qty, price in zip(product_ids, quantities, unit_prices):
            if not pid:
                continue
            product = conn.execute("SELECT * FROM products WHERE id = %s AND account_id = %s", (pid, account_id)).fetchone()
            if not product:
                continue
            quantity = _safe_float(qty or 0)
            unit_price = _safe_float(price or 0)
            if quantity <= 0:
                continue
            if product["stock"] < quantity:
                flash(translate("error_insufficient_stock"), "error")
                valid = False
                break
            line_total = quantity * unit_price
            total += line_total
            cost_total += quantity * product["cost"]
            items.append({
                "product_id": pid,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": line_total,
                "product_name": product["name"],
            })

        if not valid:
            conn.close()
            return redirect(url_for("vendas"))

        if not items:
            flash(translate("error_no_items"), "error")
            conn.close()
            return redirect(url_for("vendas"))

        total = total - discount + surcharge
        if total <= 0:
            flash("O total final da venda precisa ser maior que zero.", "error")
            conn.close()
            return redirect(url_for("vendas"))

        allow_multi = settings.get("allow_multi_payment_sale") == "1"
        payment_parts = []
        payment_methods = request.form.getlist("pay_method[]")
        payment_amounts = request.form.getlist("pay_amount[]")
        payment_installments = request.form.getlist("pay_installments[]")

        if allow_multi:
            for idx, method_name in enumerate(payment_methods):
                method_name = (method_name or "").strip()
                amount = _safe_float(payment_amounts[idx] if idx < len(payment_amounts) else 0)
                installments = _safe_int(payment_installments[idx] if idx < len(payment_installments) else 1, 1)
                if not method_name or amount <= 0:
                    continue
                payment_parts.append({"method": method_name, "amount": amount, "installments": max(1, installments)})

            if payment_parts:
                paid_total = sum(part["amount"] for part in payment_parts)
                # Compute authoritative card fees using embedded-fee formula:
                # each row amount is final (base*(1+rate/100)), so fee = final - final/(1+rate/100)
                credit_fees = 0.0
                for part in payment_parts:
                    rate = 0.0
                    if part["method"] == "Crédito" and settings.get("card_credit_surcharge_enabled") == "1":
                        rate = _safe_float(settings.get(f"card_credit_rate_{part['installments']}", 0))
                    elif part["method"] == "Débito" and settings.get("card_debit_surcharge_enabled") == "1":
                        rate = _safe_float(settings.get("card_debit_rate", 0))
                    if rate > 0:
                        credit_fees += part["amount"] - part["amount"] / (1 + rate / 100)
                if abs(paid_total - total) > 0.05:
                    flash("A soma das formas de pagamento deve ser igual ao total da venda (com ou sem juros).", "error")
                    conn.close()
                    return redirect(url_for("vendas"))
                surcharge = round(credit_fees, 2)
                payment_method = "Múltiplos"
            else:
                if payment_method == "Crédito":
                    payment_method = f"Crédito ({max(1, installments_single)}x)"
        else:
            if payment_method == "Crédito":
                payment_method = f"Crédito ({max(1, installments_single)}x)"

        has_pix_in_sale = payment_method.startswith("Pix") or any(part["method"] == "Pix" for part in payment_parts)
        if has_pix_in_sale and request.form.get("pix_confirmed") != "1":
            flash("Confirme o recebimento via Pix para concluir a venda.", "error")
            conn.close()
            return redirect(url_for("vendas"))

        if payment_method == "Múltiplos":
            payment_method = " | ".join(
                [
                    f"{part['method']} R$ {part['amount']:.2f}" + (f" ({part['installments']}x)" if part["method"] == "Crédito" else "")
                    for part in payment_parts
                ]
            )

        profit = total - cost_total
        sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            "INSERT INTO sales (account_id, date, client_id, payment_method, discount, surcharge, total, profit) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (account_id, sale_date, client_id, payment_method, discount, surcharge, total, profit),
        )
        sale_id = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('sales', 'id'))").fetchone()[0]

        for item in items:
            conn.execute(
                "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, total_price) VALUES (%s, %s, %s, %s, %s)",
                (sale_id, item["product_id"], item["quantity"], item["unit_price"], item["total_price"]),
            )
            conn.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s AND account_id = %s",
                (item["quantity"], item["product_id"], account_id),
            )
            conn.execute(
                "INSERT INTO stock_movements (account_id, product_id, quantity, movement_type, date, notes, created_by_user_id, created_by_user_name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (account_id, item["product_id"], item["quantity"], "sale", sale_date, f"Venda #{sale_id}", get_current_user_id(), session.get("user_name") or session.get("user")),
            )

        # Phase 2: cada venda gera um contas a receber rastreável no financeiro.
        existing_sale_receivable = conn.execute(
            "SELECT id FROM financial_entries WHERE account_id = %s AND source = 'sale' AND source_ref = %s LIMIT 1",
            (account_id, str(sale_id)),
        ).fetchone()
        if not existing_sale_receivable:
            sale_client = conn.execute(
                "SELECT name FROM clients WHERE id = %s AND account_id = %s LIMIT 1",
                (client_id, account_id),
            ).fetchone() if client_id else None
            sale_client_name = (sale_client["name"] if sale_client else None) or "Sem cliente"
            sale_due_date = sale_date[:10]
            conn.execute(
                "INSERT INTO financial_entries (account_id, entry_type, description, client_id, amount, due_date, status, source, source_ref, created_at, paid_at) "
                "VALUES (%s, 'receivable', %s, %s, %s, %s, 'pago', 'sale', %s, %s, %s)",
                (
                    account_id,
                    f"Venda #{sale_id} - {sale_client_name}",
                    client_id,
                    total,
                    sale_due_date,
                    str(sale_id),
                    sale_date,
                    sale_date,
                ),
            )
            receivable_id = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('financial_entries', 'id'))").fetchone()[0]
            conn.execute(
                "INSERT INTO financial_payment_history (account_id, entry_id, event_type, payment_date, payment_amount, payment_method, notes, created_by_user_name, created_at) "
                "VALUES (%s, %s, 'payment_registered_auto_sale', %s, %s, %s, %s, %s, %s)",
                (
                    account_id,
                    receivable_id,
                    sale_due_date,
                    total,
                    payment_method,
                    f"Registro automático da venda #{sale_id}",
                    session.get("user_name") or session.get("user"),
                    sale_date,
                ),
            )

        conn.commit()
        flash(translate("sale_success"), "success")

        if _to_bool(settings.get("send_sale_thank_you")) and client_id:
            client = conn.execute(
                "SELECT name, email FROM clients WHERE id = %s AND account_id = %s",
                (client_id, account_id),
            ).fetchone()
            if client and client.get("email"):
                sale_lines = [
                    f"- {item['product_name']}: {item['quantity']} x {item['unit_price']:.2f} = {item['total_price']:.2f}"
                    for item in items
                ]
                sale_body = (
                    f"Olá, {client.get('name') or 'cliente'}!\n\n"
                    f"Obrigado pela sua compra na Kdc Systems.\n"
                    f"Venda #{sale_id} em {sale_date}.\n"
                    f"Forma de pagamento: {payment_method}.\n"
                    f"Total: {total:.2f}.\n\n"
                    "Itens:\n"
                    + "\n".join(sale_lines)
                    + "\n\nAgradecemos a preferência!"
                )
                sent, err = send_email_with_settings(
                    account_id,
                    [client["email"]],
                    f"Obrigado pela compra - Venda #{sale_id}",
                    sale_body,
                )
                if sent:
                    flash(f"E-mail de agradecimento enviado para {client['email']}.", "info")
                else:
                    flash(f"Não foi possível enviar e-mail ao cliente: {err}", "error")

        if _to_bool(settings.get("send_stock_min_alert")):
            low_stock_items = []
            for item in items:
                product_state = conn.execute(
                    "SELECT name, stock, stock_min FROM products WHERE id = %s AND account_id = %s",
                    (item["product_id"], account_id),
                ).fetchone()
                if product_state and float(product_state["stock"] or 0) <= float(product_state["stock_min"] or 0):
                    low_stock_items.append(product_state)

            if low_stock_items:
                recipients = get_primary_notification_recipients(account_id)
                if recipients:
                    alert_lines = [
                        f"- {row['name']}: estoque atual {row['stock']} (mínimo {row['stock_min']})"
                        for row in low_stock_items
                    ]
                    alert_body = (
                        "Os seguintes produtos atingiram estoque mínimo após uma venda:\n\n"
                        + "\n".join(alert_lines)
                        + "\n\nVerifique a reposição no sistema."
                    )
                    sent, err = send_email_with_settings(
                        account_id,
                        recipients,
                        "Alerta de estoque mínimo",
                        alert_body,
                    )
                    if not sent:
                        flash(f"Falha ao enviar alerta de estoque mínimo: {err}", "error")

        if payment_method.startswith("Pix"):
            pix_code = f"PIX-{int(total * 100)}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Recarrega os produtos para refletir o estoque atualizado na nova venda.
        products = conn.execute(
            "SELECT p.*, u.name AS unit_name "
            "FROM products p "
            "LEFT JOIN units u ON p.unit_id = u.id "
            "WHERE p.account_id = %s AND COALESCE(p.status, 'ativo') = 'ativo' "
            "ORDER BY (SELECT COALESCE(SUM(quantity), 0) FROM sale_items si WHERE si.product_id = p.id) DESC, p.name",
            (account_id,),
        ).fetchall()

        conn.close()
        return render_template(
            "vendas.html",
            title=translate("menu_sales"),
            products=products,
            clients=clients,
            pix_code=pix_code,
            cash_summary=None,
            card_settings_json=card_settings_json,
            payment_ui_settings_json=payment_ui_settings_json,
        )

    conn.close()
    return render_template(
        "vendas.html",
        title=translate("menu_sales"),
        products=products,
        clients=clients,
        pix_code=pix_code,
        cash_summary=cash_summary,
        card_settings_json=card_settings_json,
        payment_ui_settings_json=payment_ui_settings_json,
    )


@app.route("/fechar_caixa")
def fechar_caixa():
    if not session.get("user"):
        return redirect(url_for("login"))
    account_id = get_current_account_id()
    conn = get_tenant_connection()
    products = conn.execute(
        "SELECT p.*, u.name AS unit_name "
        "FROM products p "
        "LEFT JOIN units u ON p.unit_id = u.id "
        "WHERE p.account_id = %s "
        "ORDER BY (SELECT COALESCE(SUM(quantity), 0) FROM sale_items si WHERE si.product_id = p.id) DESC, p.name",
        (account_id,),
    ).fetchall()
    clients = conn.execute("SELECT * FROM clients WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
    today = datetime.now().strftime("%Y-%m-%d")
    sales_today = conn.execute(
        "SELECT id, date, payment_method, total FROM sales WHERE account_id = %s AND date LIKE %s ORDER BY date ASC",
        (account_id, f"{today}%"),
    ).fetchall()
    cash_total = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM sales WHERE account_id = %s AND date LIKE %s AND payment_method = %s",
        (account_id, f"{today}%", "Dinheiro"),
    ).fetchone()[0]
    total_day = sum(float(sale["total"] or 0) for sale in sales_today)
    recipients = get_primary_notification_recipients(account_id)
    email_sent = False
    email_error = None

    if recipients:
        lines = [
            f"{sale['date']} | Venda #{sale['id']} | {sale['payment_method'] or 'N/A'} | R$ {float(sale['total'] or 0):.2f}"
            for sale in sales_today
        ]

        totals_by_method = {}
        for sale in sales_today:
            method = sale["payment_method"] or "N/A"
            totals_by_method[method] = totals_by_method.get(method, 0.0) + float(sale["total"] or 0)

        method_lines = [
            f"- {method}: R$ {amount:.2f}"
            for method, amount in sorted(totals_by_method.items(), key=lambda row: row[0])
        ]

        body = (
            f"Fechamento de caixa - {today}\n\n"
            "Vendas do dia:\n"
            + ("\n".join(lines) if lines else "Nenhuma venda registrada hoje.")
            + "\n\nTotalizador final:\n"
            + ("\n".join(method_lines) if method_lines else "- Nenhuma venda no período")
            + f"\n- Total em dinheiro: R$ {cash_total:.2f}"
            + f"\n- Total geral do dia: R$ {total_day:.2f}"
            + f"\n- Quantidade de vendas: {len(sales_today)}"
        )
        email_sent, email_error = send_email_with_settings(
            account_id,
            recipients,
            f"Fechamento de caixa - {today}",
            body,
        )

    conn.close()
    cash_summary = f"{translate('cash_total_message')} {cash_total:.2f}. Total geral do dia: {total_day:.2f}. "
    if recipients and email_sent:
        cash_summary += f"{translate('email_sent_to')} {', '.join(recipients)}."
    elif recipients and not email_sent:
        cash_summary += f"Falha ao enviar e-mail para {', '.join(recipients)}: {email_error}."
    else:
        cash_summary += translate('email_not_configured')
    return render_template(
        "vendas.html",
        title=translate("menu_sales"),
        products=products,
        clients=clients,
        pix_code=None,
        cash_summary=cash_summary,
    )


@app.route("/financeiro", methods=["GET", "POST"])
def financeiro():
    if not session.get("user"):
        return redirect(url_for("login"))

    account_id = get_current_account_id()
    if not account_id:
        session.clear()
        flash("Sessão inválida. Faça login novamente.", "error")
        return redirect(url_for("login"))

    try:
        conn = get_tenant_connection()
    except Exception as exc:
        logger.exception("Falha ao conectar no banco para abrir financeiro: %s", exc)
        flash("Não foi possível conectar ao banco para carregar o financeiro.", "error")
        return render_template("placeholder.html", title=translate("menu_finance"))
    generated_recurring = 0
    alert_snapshot = None
    try:
        _ensure_default_financial_categories(conn, account_id)
        generated_recurring = _run_financial_recurring_generation(conn, account_id)
        alert_snapshot = _financial_due_alert_snapshot(conn, account_id)
        # Evita dependência externa (SMTP) durante navegação do usuário no menu.
        # O envio de alerta por e-mail deve ocorrer em rotina assíncrona/scheduler.
        conn.commit()
        if generated_recurring > 0:
            flash(f"Recorrência: {generated_recurring} novo(s) título(s) gerado(s) automaticamente.", "success")
    except Exception as exc:
        conn.rollback()
        logger.exception("Falha em rotinas automáticas do financeiro: %s", exc)
        flash("Algumas rotinas automáticas do financeiro falharam. Exibindo dados disponíveis.", "error")

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        return_to = (request.form.get("return_to") or "").strip().lower()

        def _post_redirect(anchor=""):
            base = url_for("estoque_entrada") if return_to == "compras" else url_for("financeiro")
            return redirect(base + anchor)

        try:
            if action == "add_category":
                name = (request.form.get("name") or "").strip()
                kind = (request.form.get("kind") or "both").strip().lower()
                if kind not in {"payable", "receivable", "both"}:
                    kind = "both"
                if not name:
                    flash("Informe o nome da categoria financeira.", "error")
                else:
                    conn.execute(
                        "INSERT INTO financial_categories (account_id, name, kind) VALUES (%s, %s, %s)",
                        (account_id, name, kind),
                    )
                    conn.commit()
                    flash("Categoria financeira cadastrada.", "success")

            elif action == "add_entry":
                entry_type = (request.form.get("entry_type") or "").strip().lower()
                description = (request.form.get("description") or "").strip()
                category_id = request.form.get("category_id") or None
                supplier_id = request.form.get("supplier_id") or None
                client_id = request.form.get("client_id") or None
                amount = _safe_money(request.form.get("amount"), 0)
                due_date = (request.form.get("due_date") or "").strip()
                source = _normalize_financial_source(request.form.get("source") or "manual")
                is_recurring = 1 if request.form.get("is_recurring") else 0
                recurrence_days = _safe_int(request.form.get("recurrence_days") or 30, 30)

                category_mismatch = False
                if entry_type not in {"payable", "receivable"}:
                    flash("Informe o tipo do lançamento antes de salvar.", "error")

                if category_id and entry_type in {"payable", "receivable"}:
                    cat_kind_row = conn.execute(
                        "SELECT kind FROM financial_categories WHERE id = %s AND account_id = %s LIMIT 1",
                        (category_id, account_id),
                    ).fetchone()
                    if not cat_kind_row:
                        category_id = None
                    else:
                        cat_kind = (cat_kind_row["kind"] or "both").strip().lower()
                        if cat_kind not in {"both", entry_type}:
                            category_mismatch = True
                            flash("A categoria financeira não corresponde ao tipo selecionado.", "error")

                if entry_type not in {"payable", "receivable"}:
                    pass
                elif category_mismatch:
                    pass
                elif not description or amount <= 0 or not due_date:
                    flash("Preencha descrição, valor e vencimento para lançar o título.", "error")
                else:
                    if is_recurring and source == "manual":
                        source = "recurring_expense"
                    conn.execute(
                        "INSERT INTO financial_entries (account_id, entry_type, description, category_id, supplier_id, client_id, amount, due_date, status, is_recurring, recurrence_days, source, created_at, paid_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendente', %s, %s, %s, %s, NULL)",
                        (
                            account_id,
                            entry_type,
                            description,
                            category_id,
                            supplier_id,
                            client_id,
                            amount,
                            due_date,
                            is_recurring,
                            max(1, recurrence_days),
                            source,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                    conn.commit()
                    flash("Lançamento financeiro salvo.", "success")

            elif action == "register_payment":
                entry_id = request.form.get("entry_id")
                payment_date = (request.form.get("payment_date") or "").strip()[:10]
                payment_amount = _safe_money(request.form.get("payment_amount"), 0)
                payment_method = (request.form.get("payment_method") or "").strip()
                payment_notes = (request.form.get("payment_notes") or "").strip()

                entry = conn.execute(
                    "SELECT id, entry_type, description, category_id, supplier_id, client_id, amount, due_date, status, is_recurring, recurrence_days, source, source_ref "
                    "FROM financial_entries WHERE id = %s AND account_id = %s LIMIT 1",
                    (entry_id, account_id),
                ).fetchone()
                if not entry:
                    flash("Lançamento não encontrado para registrar pagamento.", "error")
                else:
                    current_status = _effective_financial_status(entry["status"], entry["due_date"])
                    if current_status == "pago":
                        flash("Este lançamento já está pago.", "info")
                    elif not payment_date or payment_amount <= 0 or not payment_method:
                        flash("Informe data, valor pago e forma de pagamento.", "error")
                    elif payment_amount > float(entry["amount"] or 0):
                        flash("Valor pago não pode ser maior que o valor do lançamento.", "error")
                    else:
                        total_amount = float(entry["amount"] or 0)
                        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        operator_name = session.get("user_name") or session.get("user")

                        if payment_amount < total_amount:
                            remaining_amount = round(total_amount - payment_amount, 2)

                            # Mantém o título original em aberto com saldo remanescente.
                            conn.execute(
                                "UPDATE financial_entries SET amount = %s, status = 'pendente', paid_at = NULL WHERE id = %s AND account_id = %s",
                                (remaining_amount, entry_id, account_id),
                            )

                            # Registra a parcela paga como título quitado para refletir no fluxo de caixa.
                            conn.execute(
                                "INSERT INTO financial_entries (account_id, entry_type, description, category_id, supplier_id, client_id, amount, due_date, status, is_recurring, recurrence_days, source, source_ref, created_at, paid_at) "
                                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pago', 0, %s, 'partial_payment', %s, %s, %s)",
                                (
                                    account_id,
                                    entry["entry_type"],
                                    f"{entry['description']} (parcial)",
                                    entry["category_id"],
                                    entry["supplier_id"],
                                    entry["client_id"],
                                    payment_amount,
                                    payment_date,
                                    max(_safe_int(entry["recurrence_days"], 30), 1),
                                    f"partial_of:{entry_id}",
                                    created_at,
                                    payment_date + " 00:00:00",
                                ),
                            )
                            partial_entry_id = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('financial_entries', 'id'))").fetchone()[0]

                            conn.execute(
                                "INSERT INTO financial_payment_history (account_id, entry_id, event_type, payment_date, payment_amount, payment_method, notes, created_by_user_name, created_at) "
                                "VALUES (%s, %s, 'payment_registered_partial', %s, %s, %s, %s, %s, %s)",
                                (
                                    account_id,
                                    entry_id,
                                    payment_date,
                                    payment_amount,
                                    payment_method,
                                    (payment_notes + " | " if payment_notes else "") + f"Saldo remanescente: R$ {remaining_amount:.2f}",
                                    operator_name,
                                    created_at,
                                ),
                            )
                            conn.execute(
                                "INSERT INTO financial_payment_history (account_id, entry_id, event_type, payment_date, payment_amount, payment_method, notes, created_by_user_name, created_at) "
                                "VALUES (%s, %s, 'payment_registered', %s, %s, %s, %s, %s, %s)",
                                (
                                    account_id,
                                    partial_entry_id,
                                    payment_date,
                                    payment_amount,
                                    payment_method,
                                    (payment_notes + " | " if payment_notes else "") + f"Parcela do lançamento #{entry_id}",
                                    operator_name,
                                    created_at,
                                ),
                            )
                            conn.commit()
                            flash(f"Pagamento parcial registrado. Restante em aberto: R$ {remaining_amount:.2f}".replace('.', ','), "success")
                        else:
                            conn.execute(
                                "UPDATE financial_entries SET status = 'pago', paid_at = %s WHERE id = %s AND account_id = %s",
                                (payment_date + " 00:00:00", entry_id, account_id),
                            )
                            conn.execute(
                                "INSERT INTO financial_payment_history (account_id, entry_id, event_type, payment_date, payment_amount, payment_method, notes, created_by_user_name, created_at) "
                                "VALUES (%s, %s, 'payment_registered', %s, %s, %s, %s, %s, %s)",
                                (
                                    account_id,
                                    entry_id,
                                    payment_date,
                                    payment_amount,
                                    payment_method,
                                    payment_notes,
                                    operator_name,
                                    created_at,
                                ),
                            )
                            conn.commit()
                            flash("Pagamento registrado com sucesso.", "success")

            elif action == "reverse_payment":
                entry_id = request.form.get("entry_id")
                reversal_notes = (request.form.get("reversal_notes") or "").strip()
                entry = conn.execute(
                    "SELECT id, amount, status FROM financial_entries WHERE id = %s AND account_id = %s LIMIT 1",
                    (entry_id, account_id),
                ).fetchone()
                if not entry:
                    flash("Lançamento não encontrado para estorno.", "error")
                elif (entry["status"] or "").strip().lower() != "pago":
                    flash("Somente lançamentos pagos podem ser estornados.", "error")
                else:
                    conn.execute(
                        "UPDATE financial_entries SET status = 'pendente', paid_at = NULL WHERE id = %s AND account_id = %s",
                        (entry_id, account_id),
                    )
                    conn.execute(
                        "INSERT INTO financial_payment_history (account_id, entry_id, event_type, payment_date, payment_amount, payment_method, notes, created_by_user_name, created_at) "
                        "VALUES (%s, %s, 'payment_reversed', %s, %s, %s, %s, %s, %s)",
                        (
                            account_id,
                            entry_id,
                            datetime.now().strftime("%Y-%m-%d"),
                            float(entry["amount"] or 0),
                            "estorno",
                            reversal_notes,
                            session.get("user_name") or session.get("user"),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                    conn.commit()
                    flash("Pagamento estornado. Lançamento retornou para pendente.", "success")

            elif action == "preview_xml":
                xml_file = request.files.get("xml_file")
                if not xml_file or not xml_file.filename:
                    flash("Selecione um arquivo XML da NF-e para importar.", "error")
                    conn.close()
                    return _post_redirect("#xml-import-compras" if return_to == "compras" else "#xml-import")
                else:
                    preview = _parse_nfe_xml(xml_file.read())
                    if not preview.get("items"):
                        flash("Não foi possível extrair itens do XML informado.", "error")
                        conn.close()
                        return _post_redirect("#xml-import-compras" if return_to == "compras" else "#xml-import")
                    else:
                        session["finance_xml_preview"] = preview
                        conn.close()
                        return _post_redirect("#xml-import-compras" if return_to == "compras" else "#xml-import")

            elif action == "cancel_xml_preview":
                session.pop("finance_xml_preview", None)
                conn.close()
                return _post_redirect("#xml-import-compras" if return_to == "compras" else "#xml-import")

            elif action == "confirm_xml":
                preview = session.get("finance_xml_preview")
                if not preview:
                    flash("Gere a pré-visualização do XML antes de confirmar.", "error")
                    conn.close()
                    return _post_redirect("#xml-import-compras" if return_to == "compras" else "#xml-import")
                else:
                    existing = None
                    if preview.get("invoice_key"):
                        existing = conn.execute(
                            "SELECT id FROM nfe_imports WHERE account_id = %s AND invoice_key = %s LIMIT 1",
                            (account_id, preview["invoice_key"]),
                        ).fetchone()
                    if existing:
                        flash("Este XML já foi importado anteriormente.", "error")
                        conn.close()
                        return _post_redirect("#xml-import-compras" if return_to == "compras" else "#xml-import")
                    else:
                        create_supplier = request.form.get("create_supplier") == "1"
                        create_products = request.form.get("create_products") == "1"
                        create_payable = request.form.get("create_payable") != "0"

                        supplier_id = None
                        if preview.get("supplier_cnpj"):
                            supplier_row = conn.execute(
                                "SELECT id FROM suppliers WHERE account_id = %s AND cnpj = %s LIMIT 1",
                                (account_id, preview["supplier_cnpj"]),
                            ).fetchone()
                            if supplier_row:
                                supplier_id = supplier_row["id"]

                        if create_supplier and not supplier_id and preview.get("supplier_name"):
                            conn.execute(
                                "INSERT INTO suppliers (account_id, name, cnpj) VALUES (%s, %s, %s)",
                                (account_id, preview.get("supplier_name"), preview.get("supplier_cnpj") or None),
                            )
                            supplier_id = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('suppliers', 'id'))").fetchone()[0]

                        category_row = conn.execute(
                            "SELECT id FROM categories WHERE account_id = %s AND name = %s LIMIT 1",
                            (account_id, "Importação XML"),
                        ).fetchone()
                        if category_row:
                            xml_category_id = category_row["id"]
                        else:
                            conn.execute(
                                "INSERT INTO categories (account_id, name) VALUES (%s, %s)",
                                (account_id, "Importação XML"),
                            )
                            xml_category_id = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('categories', 'id'))").fetchone()[0]

                        unit_row = conn.execute(
                            "SELECT id FROM units WHERE account_id = %s AND name = %s LIMIT 1",
                            (account_id, "UN"),
                        ).fetchone()
                        if unit_row:
                            xml_unit_id = unit_row["id"]
                        else:
                            conn.execute(
                                "INSERT INTO units (account_id, name) VALUES (%s, %s)",
                                (account_id, "UN"),
                            )
                            xml_unit_id = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('units', 'id'))").fetchone()[0]

                        for item in preview.get("items", []):
                            qty = max(_safe_int(round(float(item.get("quantity") or 0))), 0)
                            unit_price = float(item.get("unit_price") or 0)
                            xml_code = _normalize_product_code(item.get("code"))
                            if qty <= 0:
                                continue

                            existing_product = None
                            if xml_code:
                                existing_product = conn.execute(
                                    "SELECT id, conversion_factor FROM products WHERE account_id = %s AND product_code = %s LIMIT 1",
                                    (account_id, xml_code),
                                ).fetchone()
                            if not existing_product:
                                existing_product = conn.execute(
                                    "SELECT id, conversion_factor FROM products WHERE account_id = %s AND LOWER(name) = LOWER(%s) LIMIT 1",
                                    (account_id, item.get("name")),
                                ).fetchone()

                            factor = _normalize_conversion_factor((existing_product.get("conversion_factor") if existing_product else None) or 1)
                            qty_in_sale_units = _to_sale_units(qty, factor)
                            converted_cost = unit_price / factor if factor > 1 and unit_price > 0 else unit_price

                            if existing_product:
                                conn.execute(
                                    "UPDATE products SET stock = stock + %s, cost = %s, supplier_id = COALESCE(supplier_id, %s), product_code = COALESCE(product_code, %s) WHERE id = %s AND account_id = %s",
                                    (qty_in_sale_units, converted_cost, supplier_id, xml_code, existing_product["id"], account_id),
                                )
                                product_id = existing_product["id"]
                            elif create_products:
                                unique_code = _build_unique_product_code(conn, account_id, xml_code)
                                conn.execute(
                                    "INSERT INTO products (account_id, name, product_code, category_id, unit_id, supplier_id, cost, price, stock, stock_min, conversion_factor, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 1, 'ativo')",
                                    (account_id, item.get("name"), unique_code, xml_category_id, xml_unit_id, supplier_id, unit_price, unit_price, qty),
                                )
                                product_id = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('products', 'id'))").fetchone()[0]
                            else:
                                product_id = None

                            if product_id:
                                conn.execute(
                                    "INSERT INTO stock_movements (account_id, product_id, quantity, movement_type, date, notes, created_by_user_id, created_by_user_name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                                    (
                                        account_id,
                                        product_id,
                                        qty_in_sale_units,
                                        "xml_import",
                                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        f"Importação XML NF {preview.get('invoice_number') or '-'}",
                                        get_current_user_id(),
                                        session.get("user_name") or session.get("user"),
                                    ),
                                )

                        if create_payable:
                            conn.execute(
                                "INSERT INTO financial_entries (account_id, entry_type, description, category_id, supplier_id, amount, due_date, status, source, source_ref, created_at) "
                                "VALUES (%s, 'payable', %s, %s, %s, %s, %s, 'pendente', 'xml_import', %s, %s)",
                                (
                                    account_id,
                                    f"NF-e {preview.get('invoice_number') or '-'} - {preview.get('supplier_name') or 'Fornecedor'}",
                                    None,
                                    supplier_id,
                                    float(preview.get("total_amount") or 0),
                                    preview.get("issue_date") or datetime.now().strftime("%Y-%m-%d"),
                                    preview.get("invoice_key") or preview.get("invoice_number") or "",
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                ),
                            )

                        conn.execute(
                            "INSERT INTO nfe_imports (account_id, invoice_key, invoice_number, issue_date, supplier_cnpj, supplier_name, total_amount, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                            (
                                account_id,
                                preview.get("invoice_key") or None,
                                preview.get("invoice_number") or None,
                                preview.get("issue_date") or None,
                                preview.get("supplier_cnpj") or None,
                                preview.get("supplier_name") or None,
                                float(preview.get("total_amount") or 0),
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            ),
                        )
                        conn.commit()
                        session.pop("finance_xml_preview", None)
                        flash("XML importado com sucesso: estoque, financeiro e histórico foram atualizados.", "success")
                        conn.close()
                        return _post_redirect("#xml-import-compras" if return_to == "compras" else "#xml-import")

        except psycopg.IntegrityError:
            conn.rollback()
            flash("Registro já existe para esta conta. Revise os dados informados.", "error")
        except ET.ParseError:
            conn.rollback()
            flash("Arquivo XML inválido. Verifique se o arquivo é uma NF-e válida.", "error")
        except Exception as error:
            conn.rollback()
            logger.error(f"Erro em financeiro: {error}")
            flash("Não foi possível processar a operação financeira solicitada.", "error")

        conn.close()
        if return_to == "compras" and action in {"preview_xml", "confirm_xml", "cancel_xml_preview"}:
            return redirect(url_for("estoque_entrada") + "#xml-import-compras")
        return redirect(url_for("financeiro"))

    now_dt = datetime.now()
    today = now_dt.strftime("%Y-%m-%d")
    selected_period = (request.args.get("period") or "").strip().lower()
    selected_source_filter = _normalize_financial_source((request.args.get("source") or "").strip().lower()) if request.args.get("source") else ""
    if selected_source_filter and selected_source_filter not in FINANCIAL_SOURCE_LABELS:
        selected_source_filter = ""
    req_start_date = (request.args.get("start_date") or "").strip()
    req_end_date = (request.args.get("end_date") or "").strip()

    if selected_period == "last_7_days":
        start_date = (now_dt - timedelta(days=6)).strftime("%Y-%m-%d")
        end_date = today
    elif selected_period == "this_year":
        start_date = datetime(now_dt.year, 1, 1).strftime("%Y-%m-%d")
        end_date = today
    elif selected_period == "this_month":
        start_date = now_dt.replace(day=1).strftime("%Y-%m-%d")
        end_date = today
    elif req_start_date or req_end_date:
        selected_period = "custom"
        start_date = req_start_date or now_dt.replace(day=1).strftime("%Y-%m-%d")
        end_date = req_end_date or today
    else:
        selected_period = "this_month"
        start_date = now_dt.replace(day=1).strftime("%Y-%m-%d")
        end_date = today

    try:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        flash("Período inválido. Aplicando período padrão do mês atual.", "error")
        return redirect(url_for("financeiro") + "#cashflow-diario")

    if dt_end < dt_start:
        flash("A data final não pode ser menor que a data inicial.", "error")
        return redirect(url_for("financeiro", start_date=start_date, end_date=start_date) + "#cashflow-diario")

    month_names_pt = [
        "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ]
    finance_period_label = f"{month_names_pt[dt_start.month - 1]} {dt_start.year}"

    # Fallback seguro: garante que o template sempre tenha contexto válido.
    categories = []
    suppliers = []
    clients = []
    entries = []
    summary = {
        "payable": {"pago": 0.0, "pendente": 0.0, "vencido": 0.0},
        "receivable": {"pago": 0.0, "pendente": 0.0, "vencido": 0.0},
    }
    cashflow_rows = []
    imports_history = []
    dre = {
        "gross_revenue": 0.0,
        "discounts": 0.0,
        "net_revenue": 0.0,
        "cogs": 0.0,
        "gross_profit": 0.0,
        "operational_expenses": [],
        "operational_total": 0.0,
        "operating_result": 0.0,
        "tax_total": 0.0,
        "net_profit": 0.0,
    }

    try:
        categories = conn.execute(
            "SELECT * FROM financial_categories WHERE account_id = %s "
            "ORDER BY CASE kind WHEN 'receivable' THEN 0 WHEN 'payable' THEN 1 ELSE 2 END, name",
            (account_id,),
        ).fetchall()
        suppliers = conn.execute("SELECT id, name FROM suppliers WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()
        clients = conn.execute("SELECT id, name FROM clients WHERE account_id = %s ORDER BY name", (account_id,)).fetchall()

        entries_query = (
            "SELECT e.*, fc.name AS category_name, s.name AS supplier_name, c.name AS client_name "
            "FROM financial_entries e "
            "LEFT JOIN financial_categories fc ON e.category_id = fc.id "
            "LEFT JOIN suppliers s ON e.supplier_id = s.id "
            "LEFT JOIN clients c ON e.client_id = c.id "
            "WHERE e.account_id = %s "
        )
        entries_params = [account_id]
        if selected_source_filter:
            entries_query += "AND e.source = %s "
            entries_params.append(selected_source_filter)
        entries_query += (
            "ORDER BY CASE WHEN e.status = 'pago' THEN 2 WHEN e.due_date < %s THEN 0 ELSE 1 END, e.due_date ASC, e.id DESC "
            "LIMIT 200"
        )
        entries_params.append(today)

        entries = conn.execute(entries_query, tuple(entries_params)).fetchall()
        normalized_entries = []
        for r in entries:
            row = dict(r)
            row["status_effective"] = _effective_financial_status(row.get("status"), row.get("due_date"))
            row["due_date_display"] = _format_date_br(row.get("due_date"))
            row["source"] = _normalize_financial_source(row.get("source"))
            row["source_label"] = FINANCIAL_SOURCE_LABELS.get(row["source"], "Lançamento manual")
            row["source_ref_display"] = (str(row.get("source_ref") or "").strip())[:60]
            row["is_auto_source"] = _is_auto_financial_source(row["source"])
            normalized_entries.append(row)
        entries = normalized_entries

        summary_rows = conn.execute(
            "SELECT entry_type, "
            "COALESCE(SUM(CASE WHEN status = 'pago' THEN amount ELSE 0 END), 0) AS total_pago, "
            "COALESCE(SUM(CASE WHEN status <> 'pago' AND due_date < %s THEN amount ELSE 0 END), 0) AS total_vencido, "
            "COALESCE(SUM(CASE WHEN status <> 'pago' AND due_date >= %s THEN amount ELSE 0 END), 0) AS total_pendente "
            "FROM financial_entries WHERE account_id = %s GROUP BY entry_type",
            (today, today, account_id),
        ).fetchall()

        for row in summary_rows:
            etype = row["entry_type"] if row["entry_type"] in {"payable", "receivable"} else "payable"
            summary[etype]["pago"] = float(row["total_pago"] or 0)
            summary[etype]["vencido"] = float(row["total_vencido"] or 0)
            summary[etype]["pendente"] = float(row["total_pendente"] or 0)

        # Entrada financeira oficial: contas a receber pagas.
        # Fallback legado: vendas sem vínculo financeiro ainda são consideradas para não perder histórico.
        legacy_sales_cashflow = conn.execute(
            "SELECT SUBSTRING(s.date, 1, 10) AS day, COALESCE(SUM(s.total), 0) AS inflow "
            "FROM sales s "
            "WHERE s.account_id = %s AND SUBSTRING(s.date, 1, 10) BETWEEN %s AND %s "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM financial_entries e "
            "  WHERE e.account_id = s.account_id AND e.source = 'sale' AND e.source_ref = CAST(s.id AS TEXT)"
            ") "
            "GROUP BY SUBSTRING(s.date, 1, 10)",
            (account_id, start_date, end_date),
        ).fetchall()
        receivable_cashflow = conn.execute(
            "SELECT due_date AS day, COALESCE(SUM(amount), 0) AS inflow "
            "FROM financial_entries WHERE account_id = %s AND entry_type = 'receivable' AND status = 'pago' AND due_date BETWEEN %s AND %s "
            "GROUP BY due_date",
            (account_id, start_date, end_date),
        ).fetchall()
        payable_cashflow = conn.execute(
            "SELECT due_date AS day, COALESCE(SUM(amount), 0) AS outflow "
            "FROM financial_entries WHERE account_id = %s AND entry_type = 'payable' AND status = 'pago' AND due_date BETWEEN %s AND %s "
            "GROUP BY due_date",
            (account_id, start_date, end_date),
        ).fetchall()

        flow_map = {}
        for row in legacy_sales_cashflow:
            day = row["day"]
            flow_map.setdefault(day, {"inflow": 0.0, "outflow": 0.0})
            flow_map[day]["inflow"] += float(row["inflow"] or 0)
        for row in receivable_cashflow:
            day = row["day"]
            flow_map.setdefault(day, {"inflow": 0.0, "outflow": 0.0})
            flow_map[day]["inflow"] += float(row["inflow"] or 0)
        for row in payable_cashflow:
            day = row["day"]
            flow_map.setdefault(day, {"inflow": 0.0, "outflow": 0.0})
            flow_map[day]["outflow"] += float(row["outflow"] or 0)

        for day in sorted(flow_map.keys()):
            inflow = flow_map[day]["inflow"]
            outflow = flow_map[day]["outflow"]
            cashflow_rows.append(
                {
                    "day": day,
                    "inflow": inflow,
                    "outflow": outflow,
                    "balance": inflow - outflow,
                }
            )

        imports_history = conn.execute(
            "SELECT * FROM nfe_imports WHERE account_id = %s ORDER BY id DESC LIMIT 30",
            (account_id,),
        ).fetchall()
        imports_history = [{**dict(r), "created_date_display": _format_date_br(r["created_at"])} for r in imports_history]

        sales_period = conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS gross_revenue, COALESCE(SUM(discount), 0) AS discounts "
            "FROM sales WHERE account_id = %s AND SUBSTRING(date, 1, 10) BETWEEN %s AND %s",
            (account_id, start_date, end_date),
        ).fetchone()
        gross_revenue = float(sales_period["gross_revenue"] or 0)
        discounts = float(sales_period["discounts"] or 0)
        net_revenue = gross_revenue - discounts

        cogs_row = conn.execute(
            "SELECT COALESCE(SUM(si.quantity * p.cost), 0) AS cogs "
            "FROM sale_items si "
            "JOIN sales s ON si.sale_id = s.id "
            "JOIN products p ON si.product_id = p.id "
            "WHERE s.account_id = %s AND SUBSTRING(s.date, 1, 10) BETWEEN %s AND %s",
            (account_id, start_date, end_date),
        ).fetchone()
        cogs = float(cogs_row["cogs"] or 0)
        gross_profit = net_revenue - cogs

        expense_groups = conn.execute(
            "SELECT COALESCE(fc.name, 'Sem categoria') AS category_name, COALESCE(SUM(e.amount), 0) AS total "
            "FROM financial_entries e "
            "LEFT JOIN financial_categories fc ON e.category_id = fc.id "
            "WHERE e.account_id = %s AND e.entry_type = 'payable' AND e.status = 'pago' AND e.due_date BETWEEN %s AND %s "
            "GROUP BY fc.name ORDER BY total DESC",
            (account_id, start_date, end_date),
        ).fetchall()

        operational_expenses = []
        operational_total = 0.0
        tax_total = 0.0
        for row in expense_groups:
            name = row["category_name"] or "Sem categoria"
            total = float(row["total"] or 0)
            lowered = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode("ascii")
            if "impost" in lowered:
                tax_total += total
            else:
                operational_expenses.append({"name": name, "total": total})
                operational_total += total

        operating_result = gross_profit - operational_total
        net_profit = operating_result - tax_total

        dre = {
            "gross_revenue": gross_revenue,
            "discounts": discounts,
            "net_revenue": net_revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "operational_expenses": operational_expenses,
            "operational_total": operational_total,
            "operating_result": operating_result,
            "tax_total": tax_total,
            "net_profit": net_profit,
        }
    except Exception as exc:
        logger.exception("Falha ao carregar dados do financeiro: %s", exc)
        flash("Houve um problema ao carregar o financeiro. Exibindo dados parciais.", "error")

    xml_preview = session.get("finance_xml_preview")

    conn.close()
    finance_context = {
        "title": translate("menu_finance"),
        "entries": entries,
        "categories": categories,
        "suppliers": suppliers,
        "clients": clients,
        "summary": summary,
        "start_date": start_date,
        "end_date": end_date,
        "cashflow_rows": cashflow_rows,
        "alert_snapshot": alert_snapshot,
        "xml_preview": xml_preview,
        "imports_history": imports_history,
        "dre": dre,
        "finance_period_label": finance_period_label,
        "finance_selected_period": selected_period,
        "finance_selected_source": selected_source_filter,
        "finance_source_options": [(key, value) for key, value in FINANCIAL_SOURCE_LABELS.items()],
    }
    try:
        return render_template("financeiro.html", **finance_context)
    except Exception as exc:
        logger.exception("Falha ao renderizar template financeiro: %s", exc)
        flash("A tela de financeiro teve uma falha de visualização. Exibindo modo seguro.", "error")
        return render_template("placeholder.html", title=translate("menu_finance"))


@app.route("/relatorios")
def relatorios():
    if not session.get("user"):
        return redirect(url_for("login"))

    account_id = get_current_account_id()
    conn = get_tenant_connection()
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    section = request.args.get("section")
    report = request.args.get("report")
    stock_order = (request.args.get("stock_order") or "asc").lower()
    min_order = (request.args.get("min_order") or "asc").lower()
    stock_category = request.args.get("stock_category") or ""
    client_id = request.args.get("client_id", type=int)

    if not start_date or not end_date:
        now = datetime.now()
        first_day = now.replace(day=1)
        last_day = now.replace(day=monthrange(now.year, now.month)[1])
        start_date = first_day.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")

    sales_conditions = ["s.account_id = %s"]
    sales_params = [account_id]
    if start_date and end_date:
        try:
            dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            dt_end = datetime.strptime(end_date, "%Y-%m-%d")
            if dt_end < dt_start:
                flash("A data final não pode ser menor que a data inicial.", "error")
                now = datetime.now()
                first_day = now.replace(day=1)
                last_day = now.replace(day=monthrange(now.year, now.month)[1])
                start_date = first_day.strftime("%Y-%m-%d")
                end_date = last_day.strftime("%Y-%m-%d")
        except ValueError:
            flash(translate("error_invalid_date"), "error")
            now = datetime.now()
            first_day = now.replace(day=1)
            last_day = now.replace(day=monthrange(now.year, now.month)[1])
            start_date = first_day.strftime("%Y-%m-%d")
            end_date = last_day.strftime("%Y-%m-%d")

        sales_conditions.append("s.date BETWEEN %s AND %s")
        sales_params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])

    sales_where = " WHERE " + " AND ".join(sales_conditions)

    sales = conn.execute(
        "SELECT s.*, c.name AS client_name FROM sales s LEFT JOIN clients c ON s.client_id = c.id" + sales_where + " ORDER BY s.date DESC",
        tuple(sales_params),
    ).fetchall()
    sales = [{**dict(r), "date_display": _format_date_br(r["date"])} for r in sales]

    top_customers = conn.execute(
        "SELECT c.name, COALESCE(SUM(s.total), 0) AS total FROM sales s LEFT JOIN clients c ON s.client_id = c.id"
        + sales_where
        + " GROUP BY c.name ORDER BY total DESC LIMIT 5",
        tuple(sales_params),
    ).fetchall()
    profit_top = conn.execute(
        "SELECT p.name, COALESCE(SUM(si.total_price - p.cost * si.quantity), 0) AS profit "
        "FROM sale_items si "
        "JOIN products p ON si.product_id = p.id "
        "JOIN sales s ON si.sale_id = s.id"
        + sales_where
        + " GROUP BY p.name ORDER BY profit DESC LIMIT 5",
        tuple(sales_params),
    ).fetchall()
    payment_totals = conn.execute(
        "SELECT payment_method, COALESCE(SUM(total), 0) AS total FROM sales s"
        + sales_where
        + " GROUP BY payment_method ORDER BY payment_method ASC",
        tuple(sales_params),
    ).fetchall()
    highest_stock = conn.execute("SELECT name, stock FROM products WHERE account_id = %s ORDER BY stock DESC LIMIT 1", (account_id,)).fetchone()
    lowest_stock = conn.execute("SELECT name, stock FROM products WHERE account_id = %s ORDER BY stock ASC LIMIT 1", (account_id,)).fetchone()
    near_min_stock = conn.execute(
        "SELECT name, stock, stock_min, (stock - stock_min) AS stock_gap "
        "FROM products WHERE account_id = %s ORDER BY stock_gap ASC, stock ASC LIMIT 8",
        (account_id,),
    ).fetchall()

    sales_kpi = conn.execute(
        "SELECT COUNT(*) AS qty, COALESCE(SUM(total), 0) AS total "
        "FROM sales s" + sales_where,
        tuple(sales_params),
    ).fetchone()
    ticket_medio = 0.0
    if int(sales_kpi["qty"] or 0) > 0:
        ticket_medio = float(sales_kpi["total"] or 0) / int(sales_kpi["qty"] or 0)

    cogs_row = conn.execute(
        "SELECT COALESCE(SUM(si.quantity * p.cost), 0) AS cogs "
        "FROM sale_items si "
        "JOIN products p ON si.product_id = p.id "
        "JOIN sales s ON si.sale_id = s.id" + sales_where,
        tuple(sales_params),
    ).fetchone()

    expense_row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS expenses "
        "FROM financial_entries WHERE account_id = %s AND entry_type = 'payable' AND status = 'pago' AND due_date BETWEEN %s AND %s",
        (account_id, start_date, end_date),
    ).fetchone()

    avg_margin_row = conn.execute(
        "SELECT COALESCE(AVG(margin_percent), 0) AS avg_margin FROM products WHERE account_id = %s",
        (account_id,),
    ).fetchone()

    receitas = float(sales_kpi["total"] or 0)
    custo_mercadorias = float(cogs_row["cogs"] or 0)
    despesas_operacionais = float(expense_row["expenses"] or 0)
    lucro_bruto = receitas - custo_mercadorias
    lucro_operacional = lucro_bruto - despesas_operacionais

    relatorio_gerencial = {
        "margem_media_produtos": float(avg_margin_row["avg_margin"] or 0),
        "ticket_medio": ticket_medio,
        "produtos_mais_lucrativos": [
            {"name": row[0], "profit": float(row[1] or 0)} for row in list(profit_top)[:5]
        ],
        "dre": {
            "receitas": receitas,
            "cmv": custo_mercadorias,
            "lucro_bruto": lucro_bruto,
            "despesas": despesas_operacionais,
            "lucro_operacional": lucro_operacional,
        },
    }

    report_options = []
    report_title = None
    report_description = None
    report_headers = []
    report_rows = []
    section_title = None
    report_total = None
    report_row_classes = []
    product_gender_overall = None
    stock_categories = conn.execute(
        "SELECT id, name FROM categories WHERE account_id = %s ORDER BY name ASC",
        (account_id,),
    ).fetchall()
    selected_stock_category = stock_category
    selected_stock_order = stock_order if stock_order in ("asc", "desc") else "asc"
    selected_min_order = min_order if min_order in ("asc", "desc") else "asc"
    client_top_rows = []
    selected_client_name = None
    client_purchase_rows = []

    def get_stock_status(stock_value, stock_min_value):
        try:
            stock_num = float(stock_value or 0)
            stock_min_num = float(stock_min_value or 0)
        except (TypeError, ValueError):
            stock_num = 0.0
            stock_min_num = 0.0

        if stock_min_num <= 0:
            return "status-green", "Adequado"
        if stock_num < stock_min_num:
            return "status-red", "Abaixo do mínimo"
        if stock_num <= stock_min_num * 1.2:
            return "status-orange", "Atenção (até 20% acima)"
        if stock_num <= stock_min_num * 1.5:
            return "status-yellow", "Confortável (20% a 50% acima)"
        return "status-green", "Estoque saudável"

    if section == "fornecedores":
        section_title = translate("suppliers_report_card")
        report_options = [
            {
                "key": "supplier_by_category",
                "label": translate("supplier_by_category"),
                "description": translate("supplier_by_category_desc"),
            },
            {
                "key": "supplier_product_quantity",
                "label": translate("supplier_product_quantity"),
                "description": translate("supplier_product_quantity_desc"),
            },
            {
                "key": "supplier_sales_value",
                "label": translate("supplier_sales_value"),
                "description": translate("supplier_sales_value_desc"),
            },
        ]
        if report == "supplier_by_category":
            filter_category_name = request.args.get("filter_category_name") or ""
            report_title = translate("supplier_by_category")
            report_description = translate("supplier_by_category_desc")
            if filter_category_name:
                # drill-down: list suppliers in that category
                report_headers = ["Fornecedor", "CNPJ", "Categoria"]
                supplier_drill_rows = conn.execute(
                    "SELECT sup.name, COALESCE(sup.cnpj, '—') AS cnpj, COALESCE(cat.name, '—') AS cat_name "
                    "FROM suppliers sup "
                    "LEFT JOIN categories cat ON sup.category_id = cat.id "
                    "WHERE sup.account_id = %s AND COALESCE(cat.name, '') = %s "
                    "ORDER BY sup.name",
                    (account_id, filter_category_name),
                ).fetchall()
                report_rows = [(r["name"], r["cnpj"], r["cat_name"]) for r in supplier_drill_rows]
            else:
                report_headers = [translate("category_label"), "Total de Categorias"]
                report_rows = conn.execute(
                    "SELECT COALESCE(cat.name, %s) AS category, COUNT(sup.id) AS total "
                    "FROM suppliers sup "
                    "LEFT JOIN categories cat ON sup.category_id = cat.id "
                    "WHERE sup.account_id = %s "
                    "GROUP BY cat.name ORDER BY total DESC",
                    (translate("no_records_found"), account_id),
                ).fetchall()
        elif report == "supplier_product_quantity":
            report_title = translate("supplier_product_quantity")
            report_description = translate("supplier_product_quantity_desc")
            report_headers = [translate("supplier_name"), translate("quantity_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(sup.name, %s) AS name, COALESCE(SUM(si.quantity), 0) AS total "
                "FROM sale_items si "
                "JOIN products p ON si.product_id = p.id "
                "LEFT JOIN suppliers sup ON p.supplier_id = sup.id "
                "JOIN sales s ON si.sale_id = s.id"
                + sales_where
                + " GROUP BY sup.name ORDER BY total DESC",
                tuple([translate("no_records_found"), *sales_params]),
            ).fetchall()
        elif report == "supplier_sales_value":
            report_title = translate("supplier_sales_value")
            report_description = translate("supplier_sales_value_desc")
            report_headers = [translate("supplier_name"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(sup.name, %s) AS name, COALESCE(SUM(si.total_price), 0) AS total "
                "FROM sale_items si "
                "JOIN products p ON si.product_id = p.id "
                "LEFT JOIN suppliers sup ON p.supplier_id = sup.id "
                "JOIN sales s ON si.sale_id = s.id"
                + sales_where
                + " GROUP BY sup.name ORDER BY total DESC",
                tuple([translate("no_records_found"), *sales_params]),
            ).fetchall()
    elif section == "clientes":
        section_title = translate("clients_report_card")
        report_options = [
            {
                "key": "client_top_customers",
                "label": "Clientes que mais compram",
                "description": "Ranking por valor comprado no período com detalhamento por cliente.",
            },
            {
                "key": "client_sales_quantity",
                "label": translate("client_sales_quantity"),
                "description": translate("client_sales_quantity_desc"),
            },
            {
                "key": "client_sales_value",
                "label": translate("client_sales_value"),
                "description": translate("client_sales_value_desc"),
            },
        ]
        if report == "client_top_customers":
            report_title = "Clientes que mais compram"
            report_description = "Clique no cliente para ver todas as compras no período filtrado."
            report_headers = [translate("client_name"), translate("total_label")]
            client_top_rows = conn.execute(
                "SELECT c.id AS client_id, COALESCE(c.name, %s) AS client_name, COALESCE(SUM(s.total), 0) AS total "
                "FROM sales s "
                "LEFT JOIN clients c ON s.client_id = c.id"
                + sales_where
                + " GROUP BY c.id, c.name ORDER BY total DESC",
                tuple([translate("unknown"), *sales_params]),
            ).fetchall()

            if client_id:
                selected_client = conn.execute(
                    "SELECT id, name FROM clients WHERE id = %s AND account_id = %s",
                    (client_id, account_id),
                ).fetchone()
                if selected_client:
                    selected_client_name = selected_client["name"]
                    client_purchase_rows = conn.execute(
                        "SELECT s.date, p.name AS product_name, si.quantity, si.total_price, s.payment_method "
                        "FROM sale_items si "
                        "JOIN sales s ON si.sale_id = s.id "
                        "JOIN products p ON si.product_id = p.id "
                        "WHERE s.account_id = %s AND s.client_id = %s AND s.date BETWEEN %s AND %s "
                        "ORDER BY s.date DESC, s.id DESC",
                        (account_id, client_id, f"{start_date} 00:00:00", f"{end_date} 23:59:59"),
                    ).fetchall()
                    report_total = sum(float(row["total_price"] or 0) for row in client_purchase_rows)
        elif report == "client_sales_quantity":
            report_title = translate("client_sales_quantity")
            report_description = translate("client_sales_quantity_desc")
            report_headers = [translate("client_name"), translate("quantity_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(c.name, %s) AS name, COALESCE(SUM(si.quantity), 0) AS total "
                "FROM sale_items si JOIN sales s ON si.sale_id = s.id LEFT JOIN clients c ON s.client_id = c.id"
                + sales_where
                + " GROUP BY c.name ORDER BY total DESC",
                tuple([translate("no_records_found"), *sales_params]),
            ).fetchall()
        elif report == "client_sales_value":
            report_title = translate("client_sales_value")
            report_description = translate("client_sales_value_desc")
            report_headers = [translate("client_name"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(c.name, %s) AS name, COALESCE(SUM(si.total_price), 0) AS total "
                "FROM sale_items si JOIN sales s ON si.sale_id = s.id LEFT JOIN clients c ON s.client_id = c.id"
                + sales_where
                + " GROUP BY c.name ORDER BY total DESC",
                tuple([translate("no_records_found"), *sales_params]),
            ).fetchall()
    elif section == "produtos":
        section_title = translate("products_report_card")
        report_options = [
            {
                "key": "product_margin_list",
                "label": "Margem de lucro por produto",
                "description": "Mostra custo, preço e margem de lucro configurada por item.",
            },
            {
                "key": "product_profit_top",
                "label": "Produtos com maior lucro",
                "description": "Lucro líquido baseado em (venda - custo) x quantidade vendida.",
            },
            {
                "key": "product_sales_quantity",
                "label": translate("product_sales_quantity"),
                "description": translate("product_sales_quantity_desc"),
            },
            {
                "key": "product_sales_value",
                "label": translate("product_sales_value"),
                "description": translate("product_sales_value_desc"),
            },
            {
                "key": "product_gender_share",
                "label": translate("product_gender_share"),
                "description": "Percentual de compras por gênero para cada produto.",
            },
        ]
        if report == "product_margin_list":
            report_title = "Margem de lucro por produto"
            report_description = "Acompanhe a margem configurada no cadastro e compare com custo e preço atual."
            report_headers = [translate("product_name"), translate("cost_label"), translate("price_label"), "Margem (%)"]
            report_rows = conn.execute(
                "SELECT name, COALESCE(cost, 0), COALESCE(price, 0), COALESCE(margin_percent, 0) "
                "FROM products WHERE account_id = %s ORDER BY name ASC",
                (account_id,),
            ).fetchall()
        elif report == "product_profit_top":
            report_title = "Produtos com maior lucro"
            report_description = "Lucro líquido calculado com base no custo, venda e quantidade vendida no período."
            report_headers = [translate("product_name"), "Lucro líquido"]
            report_rows = conn.execute(
                "SELECT p.name AS product_name, "
                "COALESCE(SUM((si.unit_price - p.cost) * si.quantity), 0) AS profit "
                "FROM sale_items si "
                "JOIN products p ON si.product_id = p.id "
                "JOIN sales s ON si.sale_id = s.id"
                + sales_where
                + " GROUP BY p.name ORDER BY profit DESC",
                tuple(sales_params),
            ).fetchall()
            report_total = sum(float(row[1] or 0) for row in report_rows)
        elif report == "product_sales_quantity":
            report_title = translate("product_sales_quantity")
            report_description = translate("product_sales_quantity_desc")
            report_headers = [translate("product_name"), translate("quantity_label")]
            report_rows = conn.execute(
                "SELECT p.name AS name, COALESCE(SUM(si.quantity), 0) AS total "
                "FROM sale_items si JOIN products p ON si.product_id = p.id JOIN sales s ON si.sale_id = s.id"
                + sales_where
                + " GROUP BY p.name ORDER BY total DESC",
                tuple(sales_params),
            ).fetchall()
        elif report == "product_sales_value":
            report_title = translate("product_sales_value")
            report_description = translate("product_sales_value_desc")
            report_headers = [translate("product_name"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT p.name AS name, COALESCE(SUM(si.total_price), 0) AS total "
                "FROM sale_items si JOIN products p ON si.product_id = p.id JOIN sales s ON si.sale_id = s.id"
                + sales_where
                + " GROUP BY p.name ORDER BY total DESC",
                tuple(sales_params),
            ).fetchall()
            report_total = sum(float(row[1] or 0) for row in report_rows)
        elif report == "product_gender_share":
            report_title = translate("product_gender_share")
            report_description = "Quantidade vendida por produto com percentual por gênero e percentual geral."
            report_headers = [
                translate("product_name"),
                "Quantidade vendida",
                translate("gender_male"),
                translate("gender_female"),
                translate("gender_not_informed"),
            ]
            report_rows = conn.execute(
                "SELECT p.name AS product_name, "
                "COALESCE(SUM(CASE WHEN c.gender = 'masculino' THEN si.quantity ELSE 0 END), 0) AS qty_male, "
                "COALESCE(SUM(CASE WHEN c.gender = 'feminino' THEN si.quantity ELSE 0 END), 0) AS qty_female, "
                "COALESCE(SUM(CASE WHEN c.gender = 'nao_informar' OR c.gender IS NULL THEN si.quantity ELSE 0 END), 0) AS qty_na "
                "FROM sale_items si "
                "JOIN sales s ON si.sale_id = s.id "
                "JOIN products p ON si.product_id = p.id "
                "LEFT JOIN clients c ON s.client_id = c.id"
                + sales_where
                + " GROUP BY p.name ORDER BY p.name ASC",
                tuple(sales_params),
            ).fetchall()

            qty_male_total = 0.0
            qty_female_total = 0.0
            qty_na_total = 0.0
            percent_rows = []
            for row in report_rows:
                qty_male = float(row[1] or 0)
                qty_female = float(row[2] or 0)
                qty_na = float(row[3] or 0)
                total_qty = qty_male + qty_female + qty_na

                qty_male_total += qty_male
                qty_female_total += qty_female
                qty_na_total += qty_na

                if total_qty <= 0:
                    percent_rows.append((row[0], "0", "0 (0.0%)", "0 (0.0%)", "0 (0.0%)"))
                else:
                    percent_rows.append(
                        (
                            row[0],
                            f"{total_qty:.2f}",
                            f"{qty_male:.2f} ({(qty_male / total_qty) * 100:.1f}%)",
                            f"{qty_female:.2f} ({(qty_female / total_qty) * 100:.1f}%)",
                            f"{qty_na:.2f} ({(qty_na / total_qty) * 100:.1f}%)",
                        )
                    )
            report_rows = percent_rows

            qty_total_geral = qty_male_total + qty_female_total + qty_na_total
            if qty_total_geral > 0:
                product_gender_overall = {
                    "total": qty_total_geral,
                    "male": qty_male_total,
                    "female": qty_female_total,
                    "na": qty_na_total,
                    "male_pct": (qty_male_total / qty_total_geral) * 100,
                    "female_pct": (qty_female_total / qty_total_geral) * 100,
                    "na_pct": (qty_na_total / qty_total_geral) * 100,
                }
    elif section == "estoque":
        section_title = "Relatórios de estoque"
        report_options = [
            {
                "key": "stock_by_product",
                "label": "Posição de estoque",
                "description": "Lista completa com filtro por categoria e ordenação crescente/decrescente.",
            },
            {
                "key": "stock_by_minimum",
                "label": "Produtos abaixo do mínimo",
                "description": "Veja os itens mais urgentes ou mais folgados em relação ao mínimo.",
            },
            {
                "key": "stock_kardex",
                "label": "Movimentações (Kardex)",
                "description": "Histórico de entradas, saídas e ajustes por produto.",
            },
            {
                "key": "stock_valuation",
                "label": "Valorização do estoque",
                "description": "Quanto vale o estoque atual com base no custo médio cadastrado.",
            },
            {
                "key": "stock_top_sellers",
                "label": "Produtos mais vendidos",
                "description": "Ranking de giro por quantidade vendida no período.",
            },
            {
                "key": "stock_slow_moving",
                "label": "Produtos parados (sem giro)",
                "description": "Itens sem venda no período selecionado.",
            },
        ]

        if report == "stock_by_product":
            report_title = "Estoque por produto"
            report_description = "Use os filtros para ordenar o estoque e segmentar por categoria."
            report_headers = ["Produto", "Categoria", "Estoque atual", "Estoque mínimo", "Nível"]

            stock_params = [account_id]
            stock_where = ["p.account_id = %s"]
            if selected_stock_category:
                stock_where.append("p.category_id = %s")
                stock_params.append(selected_stock_category)

            stock_order_sql = "ASC" if selected_stock_order == "asc" else "DESC"
            stock_rows = conn.execute(
                "SELECT p.name, COALESCE(cat.name, %s) AS category_name, p.stock, p.stock_min "
                "FROM products p "
                "LEFT JOIN categories cat ON p.category_id = cat.id "
                "WHERE " + " AND ".join(stock_where) + f" ORDER BY p.stock {stock_order_sql}, p.name ASC",
                tuple([translate("no_records_found"), *stock_params]),
            ).fetchall()

            formatted_rows = []
            for row in stock_rows:
                status_class, status_text = get_stock_status(row[2], row[3])
                formatted_rows.append((row[0], row[1], row[2], row[3], status_text))
                report_row_classes.append(status_class)
            report_rows = formatted_rows

        elif report == "stock_by_minimum":
            report_title = "Estoque mínimo"
            report_description = "Ordene para identificar rapidamente o que precisa comprar agora e o que pode esperar."
            report_headers = ["Produto", "Estoque atual", "Estoque mínimo", "% acima do mínimo", "Nível"]

            stock_rows = conn.execute(
                "SELECT p.name, p.stock, p.stock_min "
                "FROM products p WHERE p.account_id = %s",
                (account_id,),
            ).fetchall()

            rows_with_ratio = []
            for row in stock_rows:
                stock_value = float(row[1] or 0)
                stock_min_value = float(row[2] or 0)
                if stock_min_value > 0:
                    ratio = ((stock_value - stock_min_value) / stock_min_value) * 100
                    ratio_text = f"{ratio:.1f}%"
                else:
                    ratio = 999999
                    ratio_text = "N/A"
                status_class, status_text = get_stock_status(stock_value, stock_min_value)
                rows_with_ratio.append((row[0], stock_value, stock_min_value, ratio, ratio_text, status_class, status_text))

            reverse_order = selected_min_order == "desc"
            rows_with_ratio.sort(key=lambda item: item[3], reverse=reverse_order)

            for item in rows_with_ratio:
                report_rows.append((item[0], item[1], item[2], item[4], item[6]))
                report_row_classes.append(item[5])
        elif report == "stock_kardex":
            report_title = "Movimentações (Kardex)"
            report_description = "Entradas, saídas e ajustes com histórico de usuário responsável."
            report_headers = ["Data", "Produto", "Tipo", "Quantidade", "Usuário", "Observação"]
            report_rows_db = conn.execute(
                "SELECT sm.date, COALESCE(p.name, %s) AS product_name, sm.movement_type, sm.quantity, COALESCE(sm.created_by_user_name, '—') AS user_name, COALESCE(sm.notes, '—') AS notes "
                "FROM stock_movements sm "
                "LEFT JOIN products p ON sm.product_id = p.id "
                "WHERE sm.account_id = %s AND SUBSTRING(sm.date, 1, 10) BETWEEN %s AND %s "
                "ORDER BY sm.date DESC, sm.id DESC LIMIT 300",
                (translate("unknown"), account_id, start_date, end_date),
            ).fetchall()
            report_rows = [
                (_format_date_br(row["date"]), row["product_name"], _movement_type_label_pt(row["movement_type"]), f"{float(row['quantity'] or 0):.3f}", row["user_name"], row["notes"])
                for row in report_rows_db
            ]
        elif report == "stock_valuation":
            report_title = "Valorização do estoque"
            report_description = "Valor por produto (estoque atual x custo unitário)."
            report_headers = ["Produto", "Estoque", "Custo unitário", "Valor em estoque"]
            valuation_rows = conn.execute(
                "SELECT name, COALESCE(stock, 0) AS stock, COALESCE(cost, 0) AS cost FROM products WHERE account_id = %s ORDER BY name",
                (account_id,),
            ).fetchall()
            report_rows = []
            total_valuation = 0.0
            for row in valuation_rows:
                value = float(row["stock"] or 0) * float(row["cost"] or 0)
                total_valuation += value
                report_rows.append((row["name"], f"{float(row['stock'] or 0):.3f}", f"R$ {float(row['cost'] or 0):.2f}", f"R$ {value:.2f}"))
            report_total = total_valuation
        elif report == "stock_top_sellers":
            report_title = "Produtos mais vendidos"
            report_description = "Ranking de quantidade vendida no período."
            report_headers = ["Produto", "Quantidade vendida", "Total vendido"]
            report_rows = conn.execute(
                "SELECT p.name AS product_name, COALESCE(SUM(si.quantity), 0) AS qty, COALESCE(SUM(si.total_price), 0) AS total_value "
                "FROM sale_items si "
                "JOIN sales s ON si.sale_id = s.id "
                "JOIN products p ON si.product_id = p.id "
                "WHERE s.account_id = %s AND SUBSTRING(s.date, 1, 10) BETWEEN %s AND %s "
                "GROUP BY p.name ORDER BY qty DESC, total_value DESC",
                (account_id, start_date, end_date),
            ).fetchall()
        elif report == "stock_slow_moving":
            report_title = "Produtos parados (sem giro)"
            report_description = "Produtos sem venda no período filtrado."
            report_headers = ["Produto", "Estoque atual", "Última venda", "Dias sem venda"]
            slow_rows = conn.execute(
                "SELECT p.id, p.name, COALESCE(p.stock, 0) AS stock, MAX(s.date) AS last_sale "
                "FROM products p "
                "LEFT JOIN sale_items si ON si.product_id = p.id "
                "LEFT JOIN sales s ON s.id = si.sale_id AND s.account_id = p.account_id "
                "WHERE p.account_id = %s "
                "GROUP BY p.id, p.name, p.stock "
                "ORDER BY p.name",
                (account_id,),
            ).fetchall()
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            report_rows = []
            for row in slow_rows:
                last_sale_raw = (row["last_sale"] or "")[:10] if row["last_sale"] else ""
                last_sale_date = _parse_iso_date(last_sale_raw)
                sold_in_period = bool(last_sale_date and start_dt <= last_sale_date <= end_dt)
                if sold_in_period:
                    continue
                days_without_sale = (datetime.now().date() - last_sale_date).days if last_sale_date else "Nunca vendeu"
                report_rows.append(
                    (
                        row["name"],
                        f"{float(row['stock'] or 0):.3f}",
                        _format_date_br(last_sale_raw) if last_sale_raw else "—",
                        str(days_without_sale),
                    )
                )
    elif section == "categorias":
        section_title = translate("categories_report_card")
        report_options = [
            {
                "key": "category_sales_quantity",
                "label": translate("category_sales_quantity"),
                "description": translate("category_sales_quantity_desc"),
            },
            {
                "key": "category_sales_value",
                "label": translate("category_sales_value"),
                "description": translate("category_sales_value_desc"),
            },
        ]
        if report == "category_sales_quantity":
            report_title = translate("category_sales_quantity")
            report_description = translate("category_sales_quantity_desc")
            report_headers = [translate("category_label"), translate("quantity_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(cat.name, %s) AS name, COALESCE(SUM(si.quantity), 0) AS total "
                "FROM sale_items si JOIN products p ON si.product_id = p.id LEFT JOIN categories cat ON p.category_id = cat.id JOIN sales s ON si.sale_id = s.id"
                + sales_where
                + " GROUP BY cat.name ORDER BY total DESC",
                tuple([translate("no_records_found"), *sales_params]),
            ).fetchall()
        elif report == "category_sales_value":
            report_title = translate("category_sales_value")
            report_description = translate("category_sales_value_desc")
            report_headers = [translate("category_label"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(cat.name, %s) AS name, COALESCE(SUM(si.total_price), 0) AS total "
                "FROM sale_items si JOIN products p ON si.product_id = p.id LEFT JOIN categories cat ON p.category_id = cat.id JOIN sales s ON si.sale_id = s.id"
                + sales_where
                + " GROUP BY cat.name ORDER BY total DESC",
                tuple([translate("no_records_found"), *sales_params]),
            ).fetchall()
            report_total = sum(float(row[1] or 0) for row in report_rows)
    elif section == "pagamentos":
        section_title = translate("payments_report_card")
        report_options = [
            {
                "key": "payment_sales_value",
                "label": translate("payment_sales_value"),
                "description": translate("payment_sales_value_desc"),
            },
        ]
        if report == "payment_sales_value":
            report_title = translate("payment_sales_value")
            report_description = translate("payment_sales_value_desc")
            report_headers = [translate("payment_method"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT payment_method, COALESCE(SUM(total), 0) AS total FROM sales s"
                + sales_where
                + " GROUP BY payment_method ORDER BY payment_method ASC",
                tuple(sales_params),
            ).fetchall()
            report_total = sum(float(row[1] or 0) for row in report_rows)

    elif section == "financeiro":
        section_title = "Relatórios financeiros"
        report_options = [
            {
                "key": "cashflow_summary",
                "label": "Fluxo de caixa",
                "description": "Resumo de entradas, saídas e saldo no período.",
            },
            {
                "key": "dre_simplificado",
                "label": "DRE simplificado",
                "description": "Demonstrativo de resultado com receitas, custos e despesas.",
            },
        ]
        if report == "cashflow_summary":
            report_title = "Fluxo de caixa"
            report_description = "Entradas e saídas do período com saldo final."
            report_headers = ["Métrica", "Valor"]

            inflow_legacy_sales = conn.execute(
                "SELECT COALESCE(SUM(s.total), 0) AS total "
                "FROM sales s "
                "WHERE s.account_id = %s AND SUBSTRING(s.date, 1, 10) BETWEEN %s AND %s "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM financial_entries e "
                "  WHERE e.account_id = s.account_id AND e.source = 'sale' AND e.source_ref = CAST(s.id AS TEXT)"
                ")",
                (account_id, start_date, end_date),
            ).fetchone()["total"]
            inflow_receivable = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM financial_entries WHERE account_id = %s AND entry_type = 'receivable' AND status = 'pago' AND due_date BETWEEN %s AND %s",
                (account_id, start_date, end_date),
            ).fetchone()["total"]
            outflow = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM financial_entries WHERE account_id = %s AND entry_type = 'payable' AND status = 'pago' AND due_date BETWEEN %s AND %s",
                (account_id, start_date, end_date),
            ).fetchone()["total"]

            total_inflow = float(inflow_legacy_sales or 0) + float(inflow_receivable or 0)
            total_outflow = float(outflow or 0)
            balance = total_inflow - total_outflow

            report_rows = [
                ("Entradas", f"R$ {total_inflow:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                ("Saídas", f"R$ {total_outflow:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                ("Saldo", f"R$ {balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
            ]
        elif report == "dre_simplificado":
            report_title = "DRE simplificado"
            report_description = "Receita líquida, CMV, despesas e lucro no período."
            report_headers = ["Linha", "Valor"]
            d = relatorio_gerencial["dre"]
            report_rows = [
                ("Receita bruta", f"R$ {d['receitas']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                ("(-) CMV", f"R$ {d['cmv']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                ("= Lucro bruto", f"R$ {d['lucro_bruto']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                ("(-) Despesas operacionais", f"R$ {d['despesas']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                ("= Lucro operacional", f"R$ {d['lucro_operacional']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
            ]

    elif section == "vendas_periodo":
        section_title = translate("sales_period_report_card")

    # Expose category-drill-down filter for template
    filter_category_name = request.args.get("filter_category_name") or ""
    sales_period_payment_totals = conn.execute(
        "SELECT payment_method, COUNT(*) AS qty, COALESCE(SUM(total), 0) AS total FROM sales s"
        + sales_where
        + " GROUP BY payment_method ORDER BY total DESC",
        tuple(sales_params),
    ).fetchall()

    sales_period_payment_cards = [
        {"key": "dinheiro", "label": "Dinheiro", "qty": 0, "total": 0.0},
        {"key": "pix", "label": "Pix", "qty": 0, "total": 0.0},
        {"key": "credito", "label": "Crédito", "qty": 0, "total": 0.0},
        {"key": "debito", "label": "Débito", "qty": 0, "total": 0.0},
    ]
    card_index = {item["key"]: item for item in sales_period_payment_cards}
    sales_period_grand_qty = 0
    sales_period_grand_total = 0.0

    for row in sales_period_payment_totals:
        method_text = (row["payment_method"] or "").strip().lower()
        method_text = unicodedata.normalize("NFKD", method_text).encode("ascii", "ignore").decode("ascii")
        qty = int(row["qty"] or 0)
        total = float(row["total"] or 0)

        sales_period_grand_qty += qty
        sales_period_grand_total += total

        if "pix" in method_text:
            card_key = "pix"
        elif "dinh" in method_text:
            card_key = "dinheiro"
        elif "cred" in method_text:
            card_key = "credito"
        elif "deb" in method_text:
            card_key = "debito"
        else:
            continue

        card_index[card_key]["qty"] += qty
        card_index[card_key]["total"] += total

    chart_data = None
    if report in ["payment_sales_value", "category_sales_value"]:
        chart_data = [{"label": row[0], "value": float(row[1])} for row in report_rows]

    chart_data_json = json.dumps(chart_data) if chart_data else None

    conn.close()

    return render_template(
        "relatorios.html",
        title=translate("menu_reports"),
        sales=sales,
        highest_stock=highest_stock,
        lowest_stock=lowest_stock,
        near_min_stock=near_min_stock,
        top_customers=top_customers,
        profit_top=profit_top,
        filters={"start_date": start_date, "end_date": end_date},
        section=section,
        section_title=section_title,
        report=report,
        report_options=report_options,
        report_title=report_title,
        report_description=report_description,
        report_headers=report_headers,
        report_rows=report_rows,
        report_total=report_total,
        report_row_classes=report_row_classes,
        stock_categories=stock_categories,
        selected_stock_category=selected_stock_category,
        selected_stock_order=selected_stock_order,
        selected_min_order=selected_min_order,
        client_top_rows=client_top_rows,
        selected_client_name=selected_client_name,
        selected_client_id=client_id,
        client_purchase_rows=client_purchase_rows,
        chart_data_json=chart_data_json,
        sales_period_payment_totals=sales_period_payment_totals,
        sales_period_payment_cards=sales_period_payment_cards,
        sales_period_grand_qty=sales_period_grand_qty,
        sales_period_grand_total=sales_period_grand_total,
        filter_category_name=filter_category_name,
        product_gender_overall=product_gender_overall,
        relatorio_gerencial=relatorio_gerencial,
    )


@app.route("/estoque/controle", methods=["GET", "POST"])
def controle_estoque():
    if not session.get("user"):
        return redirect(url_for("login"))

    account_id = get_current_account_id()
    conn = get_tenant_connection()

    products = conn.execute(
        "SELECT p.*, u.name AS unit_name FROM products p "
        "LEFT JOIN units u ON p.unit_id = u.id "
        "WHERE p.account_id = %s ORDER BY p.name",
        (account_id,),
    ).fetchall()

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        if action == "stock_adjust":
            product_id = request.form.get("product_id")
            reason = request.form.get("reason") or ""
            quantity = _safe_float(request.form.get("quantity"), 0)
            date_val = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")
            notes = (request.form.get("notes") or "").strip()

            reason_map = {r[0]: r[2] for r in ADJUSTMENT_REASONS}
            effect = reason_map.get(reason, "subtract")

            if not product_id or quantity <= 0:
                flash("Produto, motivo e quantidade são obrigatórios.", "error")
            else:
                delta = quantity if effect == "add" else -quantity
                label = next((r[1] for r in ADJUSTMENT_REASONS if r[0] == reason), reason)
                movement_type = "ajuste_entrada" if effect == "add" else "ajuste_saida"
                full_notes = f"{label}" + (f" — {notes}" if notes else "")
                conn.execute(
                    "INSERT INTO stock_movements (account_id, product_id, quantity, movement_type, date, notes, created_by_user_id, created_by_user_name) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        account_id,
                        product_id,
                        quantity,
                        movement_type,
                        date_val,
                        full_notes,
                        get_current_user_id(),
                        session.get("user_name") or session.get("user"),
                    ),
                )
                conn.execute(
                    "UPDATE products SET stock = stock + %s WHERE id = %s AND account_id = %s",
                    (delta, product_id, account_id),
                )
                conn.commit()
                flash("Ajuste de estoque registrado com sucesso.", "success")

    stock_position = conn.execute(
        "SELECT id, name, COALESCE(stock, 0) AS stock, COALESCE(stock_min, 0) AS stock_min, COALESCE(cost, 0) AS cost "
        "FROM products WHERE account_id = %s ORDER BY name",
        (account_id,),
    ).fetchall()

    below_minimum = [row for row in stock_position if float(row["stock"] or 0) < float(row["stock_min"] or 0)]
    inventory_value = sum(float(row["stock"] or 0) * float(row["cost"] or 0) for row in stock_position)

    kardex = conn.execute(
        "SELECT sm.date, COALESCE(p.name, %s) AS product_name, sm.movement_type, sm.quantity, COALESCE(sm.created_by_user_name, '—') AS user_name, COALESCE(sm.notes, '—') AS notes "
        "FROM stock_movements sm "
        "LEFT JOIN products p ON p.id = sm.product_id "
        "WHERE sm.account_id = %s "
        "ORDER BY sm.id DESC LIMIT 80",
        (translate("unknown"), account_id),
    ).fetchall()

    top_sellers = conn.execute(
        "SELECT p.name, COALESCE(SUM(si.quantity), 0) AS qty_sold "
        "FROM sale_items si "
        "JOIN sales s ON s.id = si.sale_id "
        "JOIN products p ON p.id = si.product_id "
        "WHERE s.account_id = %s AND s.date >= %s "
        "GROUP BY p.name ORDER BY qty_sold DESC LIMIT 10",
        (account_id, (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d 00:00:00")),
    ).fetchall()

    last_sale_map = {
        row["id"]: row["last_sale"]
        for row in conn.execute(
            "SELECT p.id, MAX(s.date) AS last_sale "
            "FROM products p "
            "LEFT JOIN sale_items si ON si.product_id = p.id "
            "LEFT JOIN sales s ON s.id = si.sale_id AND s.account_id = p.account_id "
            "WHERE p.account_id = %s "
            "GROUP BY p.id",
            (account_id,),
        ).fetchall()
    }

    recent_adjustments = conn.execute(
        "SELECT sm.id, sm.quantity, sm.movement_type, sm.date, sm.notes, sm.created_by_user_name, "
        "p.name AS product_name, u.name AS unit_name "
        "FROM stock_movements sm "
        "LEFT JOIN products p ON sm.product_id = p.id "
        "LEFT JOIN units u ON p.unit_id = u.id "
        "WHERE sm.account_id = %s AND sm.movement_type IN ('ajuste_entrada', 'ajuste_saida') "
        "ORDER BY sm.id DESC LIMIT 30",
        (account_id,),
    ).fetchall()

    last_move_map = {
        row["id"]: row["last_move"]
        for row in conn.execute(
            "SELECT p.id, MAX(sm.date) AS last_move "
            "FROM products p "
            "LEFT JOIN stock_movements sm ON sm.product_id = p.id AND sm.account_id = p.account_id "
            "WHERE p.account_id = %s "
            "GROUP BY p.id",
            (account_id,),
        ).fetchall()
    }

    stagnant_products = []
    no_movement_products = []
    for product in stock_position:
        pid = product["id"]
        sale_raw = (last_sale_map.get(pid) or "")[:10] if last_sale_map.get(pid) else ""
        move_raw = (last_move_map.get(pid) or "")[:10] if last_move_map.get(pid) else ""
        sale_date = _parse_iso_date(sale_raw)
        move_date = _parse_iso_date(move_raw)
        days_without_sale = (datetime.now().date() - sale_date).days if sale_date else 9999
        days_without_move = (datetime.now().date() - move_date).days if move_date else 9999
        if days_without_sale >= 30:
            stagnant_products.append({**dict(product), "days": days_without_sale if days_without_sale != 9999 else "Nunca"})
        if days_without_move >= 30:
            no_movement_products.append({**dict(product), "days": days_without_move if days_without_move != 9999 else "Nunca"})

    divergence_products = [row for row in stock_position if float(row["stock"] or 0) < 0]

    alerts = {
        "below_minimum": below_minimum,
        "no_movement": no_movement_products,
        "divergence": divergence_products,
        "no_sale": stagnant_products,
    }

    conn.close()
    return render_template(
        "controle_estoque.html",
        title="Controle de Estoque",
        products=products,
        stock_position=stock_position,
        below_minimum=below_minimum,
        inventory_value=inventory_value,
        kardex=[{**dict(row), "date_display": _format_date_br(row["date"]), "movement_type_label": _movement_type_label_pt(row["movement_type"])} for row in kardex],
        top_sellers=top_sellers,
        stagnant_products=stagnant_products,
        alerts=alerts,
        recent_adjustments=[{**dict(r), "date_display": _format_date_br(r["date"])} for r in recent_adjustments],
        adjustment_reasons_add=sorted([r for r in ADJUSTMENT_REASONS if r[2] == "add"], key=lambda x: x[1].lower()),
        adjustment_reasons_sub=sorted([r for r in ADJUSTMENT_REASONS if r[2] == "subtract"], key=lambda x: x[1].lower()),
        today=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/manual")
def manual():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template("manual.html", title=translate("manual_title"))


ADJUSTMENT_REASONS = [
    ("ajuste_inventario_add", "✓ Ajuste de inventário (acréscimo)", "add"),
    ("devolucao_cliente", "✓ Devolução de cliente", "add"),
    ("ajuste_inventario_sub", "✗ Ajuste de inventário (redução)", "subtract"),
    ("devolucao_fornecedor", "✗ Devolução ao fornecedor", "subtract"),
    ("perda", "✗ Perda (perdas gerais)", "subtract"),
    ("quebra", "✗ Quebra / Danificado", "subtract"),
    ("roubo", "✗ Roubo", "subtract"),
    ("vencimento", "✗ Vencimento / Produto vencido", "subtract"),
]


@app.route("/estoque/entrada", methods=["GET", "POST"])
def estoque_entrada():
    if not session.get("user"):
        return redirect(url_for("login"))
    account_id = get_current_account_id()
    conn = get_tenant_connection()
    products = conn.execute(
        "SELECT p.*, u.name AS unit_name FROM products p "
        "LEFT JOIN units u ON p.unit_id = u.id "
        "WHERE p.account_id = %s ORDER BY p.name",
        (account_id,),
    ).fetchall()
    suppliers = conn.execute(
        "SELECT id, name FROM suppliers WHERE account_id = %s ORDER BY name",
        (account_id,),
    ).fetchall()

    if request.method == "POST":
        action = (request.form.get("action") or "register_purchase").strip()

        if action == "register_purchase":
            product_id = request.form.get("product_id")
            try:
                quantity = float(request.form.get("quantity") or 0)
            except ValueError:
                quantity = 0
            date_val = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")
            supplier_id = request.form.get("supplier_id") or None
            notes = (request.form.get("notes") or "").strip()
            try:
                cost_per_unit = float(request.form.get("cost_per_unit") or 0)
            except ValueError:
                cost_per_unit = 0

            if not product_id or quantity <= 0:
                flash("Produto e quantidade são obrigatórios.", "error")
            else:
                product_row = conn.execute(
                    "SELECT id, conversion_factor, unit_buy FROM products WHERE id = %s AND account_id = %s",
                    (product_id, account_id),
                ).fetchone()
                factor = _normalize_conversion_factor(product_row.get("conversion_factor") if product_row else 1)
                stock_quantity = _to_sale_units(quantity, factor)
                cost_per_sale_unit = cost_per_unit / factor if factor > 1 and cost_per_unit > 0 else cost_per_unit
                conversion_note = ""
                if factor > 1:
                    conversion_note = f" | Conversão: {quantity:.3f} compra = {stock_quantity:.3f} venda"
                conn.execute(
                    "INSERT INTO stock_movements (account_id, product_id, quantity, movement_type, date, notes, created_by_user_id, created_by_user_name) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        account_id,
                        product_id,
                        stock_quantity,
                        "entrada",
                        date_val,
                        (notes or "Entrada manual") + conversion_note,
                        get_current_user_id(),
                        session.get("user_name") or session.get("user"),
                    ),
                )
                conn.execute(
                    "UPDATE products SET stock = stock + %s WHERE id = %s AND account_id = %s",
                    (stock_quantity, product_id, account_id),
                )
                if cost_per_unit > 0:
                    conn.execute(
                        "UPDATE products SET cost = %s WHERE id = %s AND account_id = %s",
                        (cost_per_sale_unit, product_id, account_id),
                    )
                conn.commit()
                flash("Compra registrada com sucesso.", "success")

        elif action == "create_purchase_order":
            product_id = request.form.get("po_product_id")
            supplier_id = request.form.get("po_supplier_id") or None
            notes = (request.form.get("po_notes") or "").strip()
            expected_date = request.form.get("po_expected_date") or datetime.now().strftime("%Y-%m-%d")
            first_due_date = request.form.get("po_first_due_date") or expected_date
            try:
                quantity = float(request.form.get("po_quantity") or 0)
            except ValueError:
                quantity = 0
            try:
                unit_cost = float(request.form.get("po_unit_cost") or 0)
            except ValueError:
                unit_cost = 0
            installments = max(1, _safe_int(request.form.get("po_installments") or 1, 1))

            if not product_id or quantity <= 0:
                flash("Pedido de compra: informe produto e quantidade.", "error")
            else:
                conn.execute(
                    "INSERT INTO purchase_orders (account_id, supplier_id, product_id, quantity, unit_cost, installments, first_due_date, expected_date, status, notes, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'aberto', %s, %s)",
                    (
                        account_id,
                        supplier_id,
                        product_id,
                        quantity,
                        unit_cost,
                        installments,
                        first_due_date,
                        expected_date,
                        notes,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                po_id = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('purchase_orders', 'id'))").fetchone()[0]

                total_amount = max(quantity * unit_cost, 0)
                if total_amount > 0 and request.form.get("po_generate_payable") == "1":
                    installment_value = total_amount / installments
                    base_due = datetime.strptime(first_due_date, "%Y-%m-%d") if first_due_date else datetime.now()
                    for idx in range(installments):
                        due_dt = base_due + timedelta(days=30 * idx)
                        conn.execute(
                            "INSERT INTO financial_entries (account_id, entry_type, description, supplier_id, amount, due_date, status, source, source_ref, created_at) "
                            "VALUES (%s, 'payable', %s, %s, %s, %s, 'pendente', 'purchase', %s, %s)",
                            (
                                account_id,
                                f"Pedido de compra #{po_id} - parcela {idx + 1}/{installments}",
                                supplier_id,
                                installment_value,
                                due_dt.strftime("%Y-%m-%d"),
                                str(po_id),
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            ),
                        )

                conn.commit()
                flash("Pedido de compra criado com sucesso.", "success")

        elif action == "receive_purchase_order":
            po_id = request.form.get("po_id")
            po = conn.execute(
                "SELECT * FROM purchase_orders WHERE id = %s AND account_id = %s",
                (po_id, account_id),
            ).fetchone()
            if not po:
                flash("Pedido de compra não encontrado.", "error")
            elif po["status"] == "recebido":
                flash("Este pedido já foi recebido.", "info")
            else:
                product_row = conn.execute(
                    "SELECT conversion_factor FROM products WHERE id = %s AND account_id = %s",
                    (po["product_id"], account_id),
                ).fetchone()
                factor = _normalize_conversion_factor(product_row.get("conversion_factor") if product_row else 1)
                stock_quantity = _to_sale_units(po["quantity"], factor)
                unit_cost_value = float(po.get("unit_cost") or 0)
                cost_per_sale_unit = unit_cost_value / factor if factor > 1 and unit_cost_value > 0 else unit_cost_value
                movement_notes = f"Recebimento do pedido de compra #{po['id']}"
                if po.get("notes"):
                    movement_notes += f" - {po['notes']}"
                if factor > 1:
                    movement_notes += f" | Conversão: {float(po['quantity'] or 0):.3f} compra = {stock_quantity:.3f} venda"
                conn.execute(
                    "INSERT INTO stock_movements (account_id, product_id, quantity, movement_type, date, notes, created_by_user_id, created_by_user_name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        account_id,
                        po["product_id"],
                        stock_quantity,
                        "entrada",
                        datetime.now().strftime("%Y-%m-%d"),
                        movement_notes,
                        get_current_user_id(),
                        session.get("user_name") or session.get("user"),
                    ),
                )
                conn.execute(
                    "UPDATE products SET stock = stock + %s WHERE id = %s AND account_id = %s",
                    (stock_quantity, po["product_id"], account_id),
                )
                if unit_cost_value > 0:
                    conn.execute(
                        "UPDATE products SET cost = %s WHERE id = %s AND account_id = %s",
                        (cost_per_sale_unit, po["product_id"], account_id),
                    )
                conn.execute(
                    "UPDATE purchase_orders SET status = 'recebido', received_at = %s WHERE id = %s AND account_id = %s",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), po_id, account_id),
                )
                conn.commit()
                flash("Pedido marcado como recebido e estoque atualizado.", "success")

        products = conn.execute(
            "SELECT p.*, u.name AS unit_name FROM products p "
            "LEFT JOIN units u ON p.unit_id = u.id "
            "WHERE p.account_id = %s ORDER BY p.name",
            (account_id,),
        ).fetchall()

    recent = conn.execute(
        "SELECT sm.id, sm.quantity, sm.date, sm.notes, "
        "p.name AS product_name, u.name AS unit_name "
        "FROM stock_movements sm "
        "LEFT JOIN products p ON sm.product_id = p.id "
        "LEFT JOIN units u ON p.unit_id = u.id "
        "WHERE sm.account_id = %s AND sm.movement_type = 'entrada' "
        "ORDER BY sm.id DESC LIMIT 30",
        (account_id,),
    ).fetchall()
    recent = [
        {**dict(r), "date_display": _format_date_br(r["date"])}
        for r in recent
    ]

    purchase_orders = conn.execute(
        "SELECT po.*, p.name AS product_name, s.name AS supplier_name "
        "FROM purchase_orders po "
        "LEFT JOIN products p ON po.product_id = p.id "
        "LEFT JOIN suppliers s ON po.supplier_id = s.id "
        "WHERE po.account_id = %s ORDER BY po.id DESC LIMIT 40",
        (account_id,),
    ).fetchall()
    purchase_orders = [
        {
            **dict(po),
            "expected_date_display": _format_date_br(po.get("expected_date")),
            "first_due_date_display": _format_date_br(po.get("first_due_date")),
            "created_at_display": _format_date_br(po.get("created_at")),
            "received_at_display": _format_date_br(po.get("received_at")),
        }
        for po in purchase_orders
    ]

    xml_preview = session.get("finance_xml_preview")

    conn.close()
    return render_template(
        "estoque_entrada.html",
        title="Compras",
        products=products,
        suppliers=suppliers,
        recent=recent,
        purchase_orders=purchase_orders,
        xml_preview=xml_preview,
        today=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/estoque/ajuste", methods=["GET", "POST"])
def estoque_ajuste():
    return redirect(url_for("controle_estoque") + "#ajuste-estoque")


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
