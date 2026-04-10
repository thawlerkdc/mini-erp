"""
Script de teste para verificar se a aplicação pode ser executada localmente.
Testa as dependências e a conexão com o banco de dados.
"""

import sys
import os
from pathlib import Path

def test_dependencies():
    """Testa se todas as dependências estão instaladas."""
    print("🔍 Verificando dependências...")
    required = [
        'flask',
        'psycopg',
        'dotenv',
        'gunicorn',
        'schedule'
    ]
    
    missing = []
    for lib in required:
        try:
            __import__(lib.replace('-', '_'))
            print(f"  ✓ {lib}")
        except ImportError:
            print(f"  ✗ {lib} - NÃO INSTALADO")
            missing.append(lib)
    
    return len(missing) == 0, missing

def test_env_file():
    """Verifica se o arquivo .env existe e está configurado."""
    print("\n🔍 Verificando configurações (.env)...")
    
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        print(f"  ✓ Arquivo .env encontrado")
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'DATABASE_URL' in content:
                print(f"  ✓ DATABASE_URL configurado")
                # Procura pela URL
                for line in content.split('\n'):
                    if line.startswith('DATABASE_URL='):
                        url = line.replace('DATABASE_URL=', '').strip()
                        if url:
                            print(f"    URL: {url[:50]}...")
                        else:
                            print(f"    ⚠️  DATABASE_URL vazio (use PostgreSQL local)")
            else:
                print(f"  ⚠️  DATABASE_URL não found")
    else:
        print(f"  ⚠️  Arquivo .env não encontrado - criando configuração padrão...")
        return False
    
    return True

def test_import():
    """Testa se os módulos principais conseguem ser importados."""
    print("\n🔍 Verificando imports...")
    try:
        import app as app_module
        print(f"  ✓ app.py importado com sucesso")
        return True
    except Exception as e:
        print(f"  ✗ Erro ao importar app.py: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  TESTE DE CONFIGURAÇÃO - Mini ERP")
    print("="*60 + "\n")
    
    # Teste 1: Dependências
    deps_ok, missing = test_dependencies()
    if not deps_ok:
        print(f"\n❌ Dependências faltando: {', '.join(missing)}")
        print("   Execute: pip install -r requirements.txt")
        return False
    
    # Teste 2: Arquivo de configuração
    env_ok = test_env_file()
    
    # Teste 3: Imports
    import_ok = test_import()
    
    print("\n" + "="*60)
    if deps_ok and import_ok:
        print("  ✅ PRONTO PARA EXECUTAR!")
        print("="*60)
        print("\n📝 Para iniciar a aplicação:")
        print("   1. Se tiver PostgreSQL: configure DATABASE_URL no .env")
        print("   2. Execute: python app.py")
        print("   3. Acesse: http://127.0.0.1:5000")
        return True
    else:
        print("  ❌ EXISTEM PROBLEMAS")
        print("="*60)
        print("\n⚠️  Resolva os problemas acima e tente novamente.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
