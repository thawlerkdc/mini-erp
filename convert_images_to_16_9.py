#!/usr/bin/env python3
"""
Script para converter imagens de previews para formato 16:9
Com corte centralizado para preservar o foco principal

Uso:
  python convert_images_to_16_9.py

As imagens atuais (1200x900) serão convertidas para:
  1920x1080 (16:9) usando crop centralizado
"""

import os
from PIL import Image

PREVIEW_DIR = os.path.join(os.path.dirname(__file__), 'static', 'img', 'previews')

# Mapeamento de formatos possíveis
# Tupla: (nome_arquivo_padrão, largura_alvo, altura_alvo)
TARGET_FORMATS = [
    ('*.png', 1920, 1080),   # 16:9 HD
    ('*.jpg', 1920, 1080),
    ('*.jpeg', 1920, 1080),
]

def get_crop_box(img_width, img_height, target_width, target_height):
    """
    Calcula as coordenadas de crop centralizado para manter proporção
    
    Args:
        img_width, img_height: Dimensões da imagem original
        target_width, target_height: Dimensões alvo
    
    Returns:
        Tupla (left, top, right, bottom) para crop
    """
    # Calcular razão de aspecto
    img_ratio = img_width / img_height
    target_ratio = target_width / target_height
    
    if img_ratio > target_ratio:
        # Imagem é mais larga que o alvo, crop horizontal
        new_width = int(img_height * target_ratio)
        left = (img_width - new_width) // 2
        top = 0
        right = left + new_width
        bottom = img_height
    else:
        # Imagem é mais alta que o alvo, crop vertical
        new_height = int(img_width / target_ratio)
        left = 0
        top = (img_height - new_height) // 2
        right = img_width
        bottom = top + new_height
    
    return (left, top, right, bottom)


def convert_image(filepath, target_width, target_height):
    """
    Converte uma imagem para o formato 16:9 com crop centralizado
    
    Args:
        filepath: Caminho da imagem
        target_width, target_height: Dimensões alvo
    """
    try:
        print(f"Processando: {os.path.basename(filepath)}")
        
        with Image.open(filepath) as img:
            original_size = img.size
            print(f"  Tamanho original: {original_size[0]}x{original_size[1]}")
            
            # Calcular crop box
            crop_box = get_crop_box(img.width, img.height, target_width, target_height)
            
            # Aplicar crop
            img_cropped = img.crop(crop_box)
            print(f"  Após crop: {img_cropped.size[0]}x{img_cropped.size[1]}")
            
            # Redimensionar para o tamanho alvo
            img_resized = img_cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
            print(f"  Tamanho final: {img_resized.size[0]}x{img_resized.size[1]}")
            
            # Salvar com qualidade alta
            img_resized.save(filepath, quality=95, optimize=True)
            print(f"  ✓ Salvo com sucesso!")
            
    except Exception as e:
        print(f"  ✗ Erro: {str(e)}")


def main():
    """Função principal"""
    print("=" * 60)
    print("Conversor de Imagens para 16:9")
    print("=" * 60)
    
    if not os.path.exists(PREVIEW_DIR):
        print(f"❌ Diretório não encontrado: {PREVIEW_DIR}")
        return
    
    print(f"\nDiretório: {PREVIEW_DIR}")
    
    # Listar arquivos PNG e JPG
    files = []
    for filename in os.listdir(PREVIEW_DIR):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            files.append(os.path.join(PREVIEW_DIR, filename))
    
    if not files:
        print("❌ Nenhuma imagem encontrada!")
        return
    
    print(f"\n📸 Encontradas {len(files)} imagem(ns)\n")
    
    # Processar cada arquivo
    for filepath in sorted(files):
        convert_image(filepath, 1920, 1080)
        print()
    
    print("=" * 60)
    print("✓ Conversão concluída!")
    print("=" * 60)


if __name__ == '__main__':
    main()
