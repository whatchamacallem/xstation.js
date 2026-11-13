# Admin Commands

## apt Packages

Install these before using the package managers below.

```
sudo apt-get update

sudo apt-get install -y build-essential libwebsockets-dev libjson-c-dev \
    libuv1-dev zlib1g-dev libssl-dev nodejs npm node-typescript shfmt   \
    bubblewrap python3-pip unzip
```

## Formatters

Install into `~/.local/bin` and `~/.npm-global/bin`.

```
pip install --user --break-system-packages pyright==1.1.414 ruff==0.16.8

npm install -g --prefix ~/.npm-global prettier
```

## Chrome for Testing

Installs into  `~/.local/share/chrome-for-testing` and then uses apt.

```
DIR_="$HOME/.local/share/chrome-for-testing"
npx --yes @puppeteer/browsers install chrome@stable --path "$DIR_"
npx --yes @puppeteer/browsers install chromedriver@stable --path "$DIR_"
sudo apt-get update
sudo apt-get satisfy -y "$(paste -sd, "$DIR_"/chrome/linux-*/chrome-linux64/deb.deps)"
"$DIR_"/chrome/linux-*/chrome-linux64/chrome --version
```
