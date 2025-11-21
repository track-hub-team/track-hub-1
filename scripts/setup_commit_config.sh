echo "Configuring git commit template..."

git config commit.template .gitmessage

echo "Git commit template configured. Now when you make a commit with git commit (without flag -m), the template will be loaded."
echo ""
echo "Installing our git hooks..."

# Comprobar si el directorio .git-hooks existe
if [ ! -d ".git-hooks" ]; then
    echo ".git-hooks directory does not exist. Please pull the latest changes from the repository first..."
    exit 1
fi

# Copiar el hook al directorio local de hooks de git
cp .git-hooks/prepare-commit-msg .git/hooks/prepare-commit-msg

# Damos permisos de ejecución al hook
chmod +x .git/hooks/prepare-commit-msg

echo "Our git hooks have been installed.Now your commits will automatically include the Jira issue reference based on your branch name."
echo ""
echo "Installing pre-commit hooks..."

# Comprobar si pre-commit está instalado (funciona para ambos casos)
if ! command -v pre-commit &> /dev/null; then
    echo "pre-commit is not installed. Installing..."
    pip install pre-commit
else
    echo "pre-commit is already installed."
fi

# Instalar los hooks definidos en .pre-commit-config.yaml
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push
echo "pre-commit hooks have been installed."
echo ""
echo "Installation complete! :)"
