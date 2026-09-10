#!/usr/bin/env bash
set -e

echo "❄️  Instalando SubZero — Financial Butler no Mac..."

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
DATA_DIR="$HOME/.subzero"

mkdir -p "$BIN_DIR"
mkdir -p "$DATA_DIR"

WRAPPER="$BIN_DIR/subzero"

cat << WRAPPER_EOF > "$WRAPPER"
#!/usr/bin/env bash
exec python3 "$REPO_DIR/scripts/subzero_cli.py" "\$@"
WRAPPER_EOF

chmod +x "$WRAPPER"
chmod +x "$REPO_DIR/scripts/subzero_cli.py"

echo "✅ Comando 'subzero' instalado em $WRAPPER"

# Inicializar banco de demonstração se não existir
if [ ! -f "$DATA_DIR/finance.db" ]; then
    echo "🌱 Inicializando banco de dados local com transações de demonstração..."
    python3 "$REPO_DIR/scripts/seed_demo.py"
fi

echo "🧪 Testando instalação..."
"$WRAPPER" audit

echo ""
echo "🎉 Pronto! O SubZero está instalado globalmente no seu Mac."
echo "Agora você ou o Hermes via Plow Latch podem rodar simplesmente:"
echo "   subzero audit"
echo "   subzero summary"
echo "   subzero import-statement extrato.csv"
