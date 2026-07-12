#!/usr/bin/env bash
# Deploy do deep-pitch num Hugging Face Space (Docker).
#
# Pré-requisito: crie o Space ANTES em https://huggingface.co/new-space
#   → Owner: seu usuário · Space name: deep-pitch · SDK: Docker · Public
#
# Uso (na raiz do repo):
#   bash scripts/deploy-hf.sh <seu-usuario-hf>
#
# O git push pedirá auth: usuário HF + um token WRITE
# (crie em https://huggingface.co/settings/tokens). Não compartilhe o token.
set -euo pipefail

USER="${1:?uso: bash scripts/deploy-hf.sh <seu-usuario-hf>}"
SPACE="deep-pitch"
REMOTE="https://huggingface.co/spaces/${USER}/${SPACE}"
TMP="$(mktemp -d)"

echo "→ Clonando o Space: ${REMOTE}"
git clone "${REMOTE}" "${TMP}/space"

echo "→ Copiando o código (app.py Gradio, requirements.txt, src)"
cp -r app.py requirements.txt src "${TMP}/space/"

echo "→ Gerando README do Space (frontmatter HF + conteúdo do projeto)"
{
  printf -- '---\ntitle: deep-pitch\nemoji: "⚽"\ncolorFrom: blue\ncolorTo: gray\nsdk: gradio\nsdk_version: "6.20.0"\napp_file: app.py\npython_version: "3.12"\npinned: false\n---\n\n'
  cat README.md
} > "${TMP}/space/README.md"

cd "${TMP}/space"
git add .
git commit -m "deploy deep-pitch"
echo "→ Push (vai pedir usuário HF + token WRITE)"
git push

echo "✓ Enviado! Acompanhe o build em: ${REMOTE}"
