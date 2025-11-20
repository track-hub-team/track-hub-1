echo "Configuring git commit template..."

git config commit.template .gitmessage

echo "Git commit template configured. Now when you make a commit with git commit (without flag -m), the template will be loaded."