from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import init_db, get_db_connection, seed_admin
from pathlib import Path
from datetime import datetime
import re
import json
import logging
import sqlite3

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "kdc_systems_secret_key"
app.config["DATABASE"] = str(Path(__file__).resolve().parent / "kdc_systems.db")

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
        "dashboard_welcome": "Bem-vindo",
        "menu_dashboard": "Dashboard",
        "menu_users": "Usuários",
        "menu_products": "Produtos",
        "menu_clients": "Clientes",
        "menu_suppliers": "Fornecedores",
        "menu_sales": "Vendas",
        "menu_reports": "Relatórios",
        "menu_manual": "Manual do sistema",
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
        "line_total": "Total da linha",
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
        "manual_title": "Manual de uso",
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
        "dashboard_welcome_text": "Use o menu para acessar cadastros, vendas, relatórios e manual.",
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
        "actions": "Ações"
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


@app.context_processor
def inject_translations():
    return {
        "t": lambda key: translate(key),
        "languages": LANGUAGES,
        "current_language": session.get("lang", DEFAULT_LANG),
    }


# Inicializa o banco de dados no carregamento do aplicativo.
#init_db(app.config["DATABASE"])
#seed_admin(app.config["DATABASE"])
from pathlib import Path

db_path = Path(app.config["DATABASE"])

if not db_path.exists():
    init_db(app.config["DATABASE"])
    seed_admin(app.config["DATABASE"])


@app.route("/set_language/<lang_code>")
def set_language(lang_code):
    if lang_code in LANGUAGES:
        session["lang"] = lang_code
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = get_db_connection(app.config["DATABASE"])
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        if user:
            session["user"] = username
            return redirect(url_for("dashboard"))
        flash(translate("invalid_login"), "error")
    return render_template("login.html", title=translate("login_title"))


@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect(url_for("login"))
    
    # Get some stats for the dashboard
    conn = get_db_connection(app.config["DATABASE"])
    total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_sales = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    conn.close()
    
    return render_template(
        "dashboard.html",
        title=translate("dashboard_title"),
        user=session.get("user"),
        welcome_text=translate("dashboard_welcome_text"),
        total_clients=total_clients,
        total_products=total_products,
        total_sales=total_sales,
    )


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
            conn = get_db_connection(app.config["DATABASE"])
            user = conn.execute(
                "SELECT id, name FROM users WHERE username = ? AND email = ?", 
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


@app.route("/cadastro/<entity>", methods=["GET", "POST"])
def cadastro(entity):
    if not session.get("user"):
        return redirect(url_for("login"))
    entity = entity.lower()
    conn = get_db_connection(app.config["DATABASE"])
    rows = []
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    units = conn.execute("SELECT * FROM units ORDER BY name").fetchall()
    suppliers = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    edit_id = request.args.get("edit_id") or request.form.get("edit_id")
    edit_data = None

    # Carregar dados para edição se edit_id estiver presente
    if edit_id:
        if entity == "usuarios":
            edit_data = dict(conn.execute("SELECT * FROM users WHERE id = ?", (edit_id,)).fetchone() or {})
        elif entity == "produtos":
            edit_data = dict(conn.execute("SELECT * FROM products WHERE id = ?", (edit_id,)).fetchone() or {})
        elif entity == "clientes":
            edit_data = dict(conn.execute("SELECT * FROM clients WHERE id = ?", (edit_id,)).fetchone() or {})
        elif entity == "fornecedores":
            edit_data = dict(conn.execute("SELECT * FROM suppliers WHERE id = ?", (edit_id,)).fetchone() or {})
        elif entity == "categorias":
            edit_data = dict(conn.execute("SELECT * FROM categories WHERE id = ?", (edit_id,)).fetchone() or {})
        elif entity == "unidades":
            edit_data = dict(conn.execute("SELECT * FROM units WHERE id = ?", (edit_id,)).fetchone() or {})

    if request.method == "POST":
        try:
            # Verificar se é delete
            if request.form.get("delete_id"):
                delete_id = request.form.get("delete_id")
                if entity == "usuarios":
                    conn.execute("DELETE FROM users WHERE id = ?", (delete_id,))
                    conn.commit()
                    flash("Registro deletado com sucesso", "success")
                elif entity == "produtos":
                    conn.execute("DELETE FROM products WHERE id = ?", (delete_id,))
                    conn.commit()
                    flash("Registro deletado com sucesso", "success")
                elif entity == "clientes":
                    conn.execute("DELETE FROM clients WHERE id = ?", (delete_id,))
                    conn.commit()
                    flash("Registro deletado com sucesso", "success")
                elif entity == "fornecedores":
                    conn.execute("DELETE FROM suppliers WHERE id = ?", (delete_id,))
                    conn.commit()
                    flash("Registro deletado com sucesso", "success")
                elif entity == "categorias":
                    # Verificar se a categoria está sendo usada
                    used_in_products = conn.execute("SELECT COUNT(*) FROM products WHERE category_id = ?", (delete_id,)).fetchone()[0]
                    used_in_suppliers = conn.execute("SELECT COUNT(*) FROM suppliers WHERE category_id = ?", (delete_id,)).fetchone()[0]
                    if used_in_products > 0 or used_in_suppliers > 0:
                        flash("Não é possível deletar esta categoria pois está sendo usada", "error")
                    else:
                        conn.execute("DELETE FROM categories WHERE id = ?", (delete_id,))
                        conn.commit()
                        flash("Registro deletado com sucesso", "success")
                elif entity == "unidades":
                    # Verificar se a unidade está sendo usada
                    used_in_products = conn.execute("SELECT COUNT(*) FROM products WHERE unit_id = ?", (delete_id,)).fetchone()[0]
                    if used_in_products > 0:
                        flash("Não é possível deletar esta unidade pois está sendo usada", "error")
                    else:
                        conn.execute("DELETE FROM units WHERE id = ?", (delete_id,))
                        conn.commit()
                        flash("Registro deletado com sucesso", "success")
                conn.close()
                return redirect(url_for("cadastro", entity=entity))
            
            # Verificar se é reset de senha (usuários)
            if entity == "usuarios" and request.form.get("action") == "reset":
                reset_id = request.form.get("reset_id")
                reset_password = request.form.get("reset_password")
                if reset_id and reset_password:
                    conn.execute("UPDATE users SET password = ? WHERE id = ?", (reset_password, reset_id))
                    conn.commit()
                    flash(translate("record_saved"), "success")
            
            # Insert ou Update
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
                            # Update
                            if password:
                                conn.execute(
                                    "UPDATE users SET name = ?, password = ?, email = ? WHERE id = ?",
                                    (name, password, email, edit_id_form)
                                )
                            else:
                                conn.execute(
                                    "UPDATE users SET name = ?, email = ? WHERE id = ?",
                                    (name, email, edit_id_form)
                                )
                        else:
                            # Insert
                            if not password:
                                flash("Senha é obrigatória para novo usuário", "error")
                            else:
                                conn.execute(
                                    "INSERT INTO users (name, username, password, email) VALUES (?, ?, ?, ?)",
                                    (name, username, password, email)
                                )
                        if not (edit_id_form and not password):
                            conn.commit()
                            flash(translate("record_saved"), "success")
                            conn.close()
                            return redirect(url_for("cadastro", entity=entity))
                    except sqlite3.IntegrityError:
                        flash("Este login já existe", "error")
                        
            elif entity == "produtos":
                new_category_name = request.form.get("new_category_name")
                if new_category_name:
                    try:
                        conn.execute("INSERT INTO categories (name) VALUES (?)", (new_category_name.strip(),))
                        conn.commit()
                        flash(translate("record_saved"), "success")
                    except sqlite3.IntegrityError:
                        flash("Esta categoria já existe", "error")
                    conn.close()
                    return redirect(url_for("cadastro", entity=entity))

                new_unit_name = request.form.get("new_unit_name")
                if new_unit_name:
                    try:
                        conn.execute("INSERT INTO units (name) VALUES (?)", (new_unit_name.strip(),))
                        conn.commit()
                        flash(translate("record_saved"), "success")
                    except sqlite3.IntegrityError:
                        flash("Esta unidade já existe", "error")
                    conn.close()
                    return redirect(url_for("cadastro", entity=entity))

                name = request.form.get("name")
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
                    if edit_id_form:
                        # Update
                        conn.execute(
                            "UPDATE products SET name = ?, category_id = ?, unit_id = ?, supplier_id = ?, cost = ?, price = ?, stock = ?, stock_min = ?, expiration_date = ? WHERE id = ?",
                            (name, category_id, unit_id, supplier_id, cost, price, stock, stock_min, expiration_date, edit_id_form)
                        )
                    else:
                        # Insert
                        conn.execute(
                            "INSERT INTO products (name, category_id, unit_id, supplier_id, cost, price, stock, stock_min, expiration_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (name, category_id, unit_id, supplier_id, cost, price, stock, stock_min, expiration_date)
                        )
                    conn.commit()
                    flash(translate("record_saved"), "success")
                    conn.close()
                    return redirect(url_for("cadastro", entity=entity))
                else:
                    flash("Preencha todos os campos obrigatórios", "error")
                    
            elif entity == "clientes":
                name = request.form.get("name")
                cpf = request.form.get("cpf") or ""
                street = request.form.get("street")
                number = request.form.get("number")
                complement = request.form.get("complement")
                neighborhood = request.form.get("neighborhood")
                city = request.form.get("city")
                state = request.form.get("state") or ""
                country = request.form.get("country")
                postal_code = request.form.get("postal_code") or ""
                edit_id_form = request.form.get("edit_id")
                cpf = re.sub(r"\D", "", cpf)[:11]
                postal_code = re.sub(r"\D", "", postal_code)[:8]
                state = re.sub(r"[^A-Za-z]", "", state).upper()[:2]
                
                if name:
                    if edit_id_form:
                        # Update
                        conn.execute(
                            "UPDATE clients SET name = ?, cpf = ?, street = ?, number = ?, complement = ?, neighborhood = ?, city = ?, state = ?, country = ?, postal_code = ? WHERE id = ?",
                            (name, cpf, street, number, complement, neighborhood, city, state, country, postal_code, edit_id_form)
                        )
                    else:
                        # Insert
                        conn.execute(
                            "INSERT INTO clients (name, cpf, street, number, complement, neighborhood, city, state, country, postal_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (name, cpf, street, number, complement, neighborhood, city, state, country, postal_code)
                        )
                    conn.commit()
                    flash(translate("record_saved"), "success")
                    conn.close()
                    return redirect(url_for("cadastro", entity=entity))
                else:
                    flash("Nome é obrigatório", "error")
                    
            elif entity == "fornecedores":
                new_category_name = request.form.get("new_category_name")
                if new_category_name:
                    try:
                        conn.execute("INSERT INTO categories (name) VALUES (?)", (new_category_name.strip(),))
                        conn.commit()
                        flash(translate("record_saved"), "success")
                    except sqlite3.IntegrityError:
                        flash("Esta categoria já existe", "error")
                    conn.close()
                    return redirect(url_for("cadastro", entity=entity))

                name = request.form.get("name")
                cnpj = request.form.get("cnpj") or ""
                street = request.form.get("street")
                number = request.form.get("number")
                complement = request.form.get("complement")
                neighborhood = request.form.get("neighborhood")
                city = request.form.get("city")
                state = request.form.get("state") or ""
                country = request.form.get("country")
                postal_code = request.form.get("postal_code") or ""
                category_id = request.form.get("category_id")
                edit_id_form = request.form.get("edit_id")
                cnpj = re.sub(r"\D", "", cnpj)[:14]
                postal_code = re.sub(r"\D", "", postal_code)[:8]
                state = re.sub(r"[^A-Za-z]", "", state).upper()[:2]
                
                if name and category_id:
                    if edit_id_form:
                        # Update
                        conn.execute(
                            "UPDATE suppliers SET name = ?, cnpj = ?, street = ?, number = ?, complement = ?, neighborhood = ?, city = ?, state = ?, country = ?, postal_code = ?, category_id = ? WHERE id = ?",
                            (name, cnpj, street, number, complement, neighborhood, city, state, country, postal_code, category_id, edit_id_form)
                        )
                    else:
                        # Insert
                        conn.execute(
                            "INSERT INTO suppliers (name, cnpj, street, number, complement, neighborhood, city, state, country, postal_code, category_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (name, cnpj, street, number, complement, neighborhood, city, state, country, postal_code, category_id)
                        )
                    conn.commit()
                    flash(translate("record_saved"), "success")
                    conn.close()
                    return redirect(url_for("cadastro", entity=entity))
                else:
                    flash("Nome e Categoria são obrigatórios", "error")
                    
            elif entity == "categorias":
                name = request.form.get("name")
                edit_id_form = request.form.get("edit_id")
                
                if name:
                    if edit_id_form:
                        # Update
                        try:
                            conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, edit_id_form))
                            conn.commit()
                        except sqlite3.IntegrityError:
                            flash("Esta categoria já existe", "error")
                            conn.close()
                            return render_template(
                                "cadastro.html",
                                title=get_entity_title(entity),
                                entity=entity,
                                rows=[],
                                categories=categories,
                                units=units,
                                edit_id=edit_id_form,
                                edit_data=edit_data,
                            )
                    else:
                        # Insert
                        try:
                            conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                            conn.commit()
                        except sqlite3.IntegrityError:
                            flash("Esta categoria já existe", "error")
                    if not (edit_id_form and conn):
                        flash(translate("record_saved"), "success")
                    conn.close()
                    return redirect(url_for("cadastro", entity=entity))
                else:
                    flash("Nome é obrigatório", "error")
                    
            elif entity == "unidades":
                name = request.form.get("name")
                edit_id_form = request.form.get("edit_id")
                
                if name:
                    if edit_id_form:
                        # Update
                        try:
                            conn.execute("UPDATE units SET name = ? WHERE id = ?", (name, edit_id_form))
                            conn.commit()
                        except sqlite3.IntegrityError:
                            flash("Esta unidade já existe", "error")
                            conn.close()
                            return render_template(
                                "cadastro.html",
                                title=get_entity_title(entity),
                                entity=entity,
                                rows=[],
                                categories=categories,
                                units=units,
                                edit_id=edit_id_form,
                                edit_data=edit_data,
                            )
                    else:
                        # Insert
                        try:
                            conn.execute("INSERT INTO units (name) VALUES (?)", (name,))
                            conn.commit()
                        except sqlite3.IntegrityError:
                            flash("Esta unidade já existe", "error")
                    if not (edit_id_form and conn):
                        flash(translate("record_saved"), "success")
                    conn.close()
                    return redirect(url_for("cadastro", entity=entity))
                else:
                    flash("Nome é obrigatório", "error")
        except Exception as e:
            logger.error(f"Erro ao processar cadastro: {e}")
            flash(translate("error_required_fields"), "error")

    # GET - Buscar dados
    if entity == "usuarios":
        rows = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
    elif entity == "produtos":
        rows = conn.execute(
            "SELECT p.*, c.name AS category_name, u.name AS unit_name, s.name AS supplier_name FROM products p LEFT JOIN categories c ON p.category_id = c.id LEFT JOIN units u ON p.unit_id = u.id LEFT JOIN suppliers s ON p.supplier_id = s.id ORDER BY p.name"
        ).fetchall()
    elif entity == "clientes":
        rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    elif entity == "fornecedores":
        rows = conn.execute(
            "SELECT s.*, c.name AS category_name FROM suppliers s LEFT JOIN categories c ON s.category_id = c.id ORDER BY s.name"
        ).fetchall()
    elif entity == "categorias":
        rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    elif entity == "unidades":
        rows = conn.execute("SELECT * FROM units ORDER BY name").fetchall()
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
        edit_id=edit_id,
        edit_data=edit_data,
    )


@app.route("/vendas", methods=["GET", "POST"])
def vendas():
    if not session.get("user"):
        return redirect(url_for("login"))
    conn = get_db_connection(app.config["DATABASE"])
    products = conn.execute(
        "SELECT p.*, u.name AS unit_name FROM products p LEFT JOIN units u ON p.unit_id = u.id ORDER BY (SELECT IFNULL(SUM(quantity), 0) FROM sale_items si WHERE si.product_id = p.id) DESC, p.name"
    ).fetchall()
    clients = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    pix_code = None
    cash_summary = None

    if request.method == "POST":
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")
        discount = float(request.form.get("discount") or 0)
        surcharge = float(request.form.get("surcharge") or 0)
        payment_method = request.form.get("payment_method")
        payment_received = float(request.form.get("payment_received") or 0)
        client_id = request.form.get("client_id") or None
        items = []
        total = 0
        cost_total = 0
        valid = True

        for pid, qty, price in zip(product_ids, quantities, unit_prices):
            if not pid:
                continue
            product = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
            if not product:
                continue
            quantity = float(qty or 0)
            unit_price = float(price or 0)
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
        profit = total - cost_total
        sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            "INSERT INTO sales (date, client_id, payment_method, discount, surcharge, total, profit) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sale_date, client_id, payment_method, discount, surcharge, total, profit),
        )
        sale_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for item in items:
            conn.execute(
                "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?)",
                (sale_id, item["product_id"], item["quantity"], item["unit_price"], item["total_price"]),
            )
            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
            conn.execute(
                "INSERT INTO stock_movements (product_id, quantity, movement_type, date, notes) VALUES (?, ?, ?, ?, ?)",
                (item["product_id"], item["quantity"], "sale", sale_date, f"Venda #{sale_id}"),
            )

        conn.commit()
        flash(translate("sale_success"), "success")

        if payment_method == "Pix":
            pix_code = f"PIX-{int(total * 100)}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        conn.close()
        return render_template(
            "vendas.html",
            title=translate("menu_sales"),
            products=products,
            clients=clients,
            pix_code=pix_code,
            cash_summary=None,
        )

    conn.close()
    return render_template(
        "vendas.html",
        title=translate("menu_sales"),
        products=products,
        clients=clients,
        pix_code=pix_code,
        cash_summary=cash_summary,
    )


@app.route("/fechar_caixa")
def fechar_caixa():
    if not session.get("user"):
        return redirect(url_for("login"))
    conn = get_db_connection(app.config["DATABASE"])
    products = conn.execute(
        "SELECT p.*, u.name AS unit_name FROM products p LEFT JOIN units u ON p.unit_id = u.id ORDER BY (SELECT IFNULL(SUM(quantity), 0) FROM sale_items si WHERE si.product_id = p.id) DESC, p.name"
    ).fetchall()
    clients = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    today = datetime.now().strftime("%Y-%m-%d")
    cash_total = conn.execute(
        "SELECT IFNULL(SUM(total), 0) FROM sales WHERE date LIKE ? AND payment_method = ?", (f"{today}%", "Dinheiro")
    ).fetchone()[0]
    user = conn.execute("SELECT email FROM users WHERE username = ?", (session["user"],)).fetchone()
    email = user["email"] if user else None
    conn.close()
    cash_summary = f"{translate('cash_total_message')} {cash_total:.2f}. "
    if email:
        cash_summary += f"{translate('email_sent_to')} {email}."
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


@app.route("/relatorios")
def relatorios():
    if not session.get("user"):
        return redirect(url_for("login"))
    conn = get_db_connection(app.config["DATABASE"])
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    section = request.args.get("section")
    report = request.args.get("report")

    date_clause = ""
    date_params = []
    if start_date and end_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
            date_clause = " WHERE date BETWEEN ? AND ?"
            date_params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
        except ValueError:
            flash(translate("error_invalid_date"), "error")

    query = "SELECT s.*, c.name AS client_name FROM sales s LEFT JOIN clients c ON s.client_id = c.id"
    query += date_clause + " ORDER BY s.date DESC"
    sales = conn.execute(query, date_params).fetchall()

    top_customers = conn.execute(
        "SELECT c.name, IFNULL(SUM(s.total), 0) AS total FROM sales s LEFT JOIN clients c ON s.client_id = c.id"
        + date_clause
        + " GROUP BY c.name ORDER BY total DESC LIMIT 5",
        date_params,
    ).fetchall()
    profit_top = conn.execute(
        "SELECT p.name, IFNULL(SUM(si.total_price - p.cost * si.quantity), 0) AS profit FROM sale_items si JOIN products p ON si.product_id = p.id"
        + (" JOIN sales s ON si.sale_id = s.id" if date_clause else "")
        + date_clause.replace(" WHERE", " WHERE s.")
        + " GROUP BY p.name ORDER BY profit DESC LIMIT 5",
        ([*date_params] if date_clause else []),
    ).fetchall()
    payment_totals = conn.execute(
        "SELECT payment_method, IFNULL(SUM(total), 0) AS total FROM sales"
        + date_clause
        + " GROUP BY payment_method",
        date_params,
    ).fetchall()
    highest_stock = conn.execute("SELECT name FROM products ORDER BY stock DESC LIMIT 1").fetchone()
    lowest_stock = conn.execute("SELECT name FROM products ORDER BY stock ASC LIMIT 1").fetchone()

    report_options = []
    report_title = None
    report_description = None
    report_headers = []
    report_rows = []
    section_title = None

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
            report_title = translate("supplier_by_category")
            report_description = translate("supplier_by_category_desc")
            report_headers = [translate("category_label"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(cat.name, ?) AS category, COUNT(s.id) AS total FROM suppliers s LEFT JOIN categories cat ON s.category_id = cat.id GROUP BY category ORDER BY total DESC",
                (translate("no_records_found"),),
            ).fetchall()
        elif report == "supplier_product_quantity":
            report_title = translate("supplier_product_quantity")
            report_description = translate("supplier_product_quantity_desc")
            report_headers = [translate("supplier_name"), translate("quantity_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(s.name, ?) AS name, IFNULL(SUM(si.quantity), 0) AS total FROM sale_items si JOIN products p ON si.product_id = p.id LEFT JOIN suppliers s ON p.supplier_id = s.id JOIN sales sale ON si.sale_id = sale.id"
                + (date_clause.replace(" WHERE", " WHERE sale.") if date_clause else "")
                + " GROUP BY s.name ORDER BY total DESC",
                ([translate("no_records_found")] + date_params if date_clause else [translate("no_records_found")]),
            ).fetchall()
        elif report == "supplier_sales_value":
            report_title = translate("supplier_sales_value")
            report_description = translate("supplier_sales_value_desc")
            report_headers = [translate("supplier_name"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(s.name, ?) AS name, IFNULL(SUM(si.total_price), 0) AS total FROM sale_items si JOIN products p ON si.product_id = p.id LEFT JOIN suppliers s ON p.supplier_id = s.id JOIN sales sale ON si.sale_id = sale.id"
                + (date_clause.replace(" WHERE", " WHERE sale.") if date_clause else "")
                + " GROUP BY s.name ORDER BY total DESC",
                ([translate("no_records_found")] + date_params if date_clause else [translate("no_records_found")]),
            ).fetchall()
    elif section == "clientes":
        section_title = translate("clients_report_card")
        report_options = [
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
        if report == "client_sales_quantity":
            report_title = translate("client_sales_quantity")
            report_description = translate("client_sales_quantity_desc")
            report_headers = [translate("client_name"), translate("quantity_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(c.name, ?) AS name, IFNULL(SUM(si.quantity), 0) AS total FROM sale_items si JOIN sales s ON si.sale_id = s.id LEFT JOIN clients c ON s.client_id = c.id"
                + (date_clause.replace(" WHERE", " WHERE s.") if date_clause else "")
                + " GROUP BY c.name ORDER BY total DESC",
                ([translate("no_records_found")] + date_params if date_clause else [translate("no_records_found")]),
            ).fetchall()
        elif report == "client_sales_value":
            report_title = translate("client_sales_value")
            report_description = translate("client_sales_value_desc")
            report_headers = [translate("client_name"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(c.name, ?) AS name, IFNULL(SUM(si.total_price), 0) AS total FROM sale_items si JOIN sales s ON si.sale_id = s.id LEFT JOIN clients c ON s.client_id = c.id"
                + (date_clause.replace(" WHERE", " WHERE s.") if date_clause else "")
                + " GROUP BY c.name ORDER BY total DESC",
                ([translate("no_records_found")] + date_params if date_clause else [translate("no_records_found")]),
            ).fetchall()
    elif section == "produtos":
        section_title = translate("products_report_card")
        report_options = [
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
        ]
        if report == "product_sales_quantity":
            report_title = translate("product_sales_quantity")
            report_description = translate("product_sales_quantity_desc")
            report_headers = [translate("product_name"), translate("quantity_label")]
            report_rows = conn.execute(
                "SELECT p.name AS name, IFNULL(SUM(si.quantity), 0) AS total FROM sale_items si JOIN products p ON si.product_id = p.id JOIN sales s ON si.sale_id = s.id"
                + (date_clause.replace(" WHERE", " WHERE s.") if date_clause else "")
                + " GROUP BY p.name ORDER BY total DESC",
                date_params,
            ).fetchall()
        elif report == "product_sales_value":
            report_title = translate("product_sales_value")
            report_description = translate("product_sales_value_desc")
            report_headers = [translate("product_name"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT p.name AS name, IFNULL(SUM(si.total_price), 0) AS total FROM sale_items si JOIN products p ON si.product_id = p.id JOIN sales s ON si.sale_id = s.id"
                + (date_clause.replace(" WHERE", " WHERE s.") if date_clause else "")
                + " GROUP BY p.name ORDER BY total DESC",
                date_params,
            ).fetchall()
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
                "SELECT COALESCE(cat.name, ?) AS name, IFNULL(SUM(si.quantity), 0) AS total FROM sale_items si JOIN products p ON si.product_id = p.id LEFT JOIN categories cat ON p.category_id = cat.id JOIN sales s ON si.sale_id = s.id"
                + (date_clause.replace(" WHERE", " WHERE s.") if date_clause else "")
                + " GROUP BY cat.name ORDER BY total DESC",
                ([translate("no_records_found")] + date_params if date_clause else [translate("no_records_found")]),
            ).fetchall()
        elif report == "category_sales_value":
            report_title = translate("category_sales_value")
            report_description = translate("category_sales_value_desc")
            report_headers = [translate("category_label"), translate("total_label")]
            report_rows = conn.execute(
                "SELECT COALESCE(cat.name, ?) AS name, IFNULL(SUM(si.total_price), 0) AS total FROM sale_items si JOIN products p ON si.product_id = p.id LEFT JOIN categories cat ON p.category_id = cat.id JOIN sales s ON si.sale_id = s.id"
                + (date_clause.replace(" WHERE", " WHERE s.") if date_clause else "")
                + " GROUP BY cat.name ORDER BY total DESC",
                ([translate("no_records_found")] + date_params if date_clause else [translate("no_records_found")]),
            ).fetchall()
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
                "SELECT payment_method, IFNULL(SUM(total), 0) AS total FROM sales"
                + date_clause
                + " GROUP BY payment_method ORDER BY total DESC",
                date_params,
            ).fetchall()

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
        top_customers=top_customers,
        profit_top=profit_top,
        payment_totals=payment_totals,
        filters={"start_date": start_date, "end_date": end_date},
        section=section,
        section_title=section_title,
        report=report,
        report_options=report_options,
        report_title=report_title,
        report_description=report_description,
        report_headers=report_headers,
        report_rows=report_rows,
        chart_data_json=chart_data_json,
    )


@app.route("/manual")
def manual():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template("manual.html", title=translate("manual_title"))


if __name__ == "__main__":
    app.run(debug=True)
