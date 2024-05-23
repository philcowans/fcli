# syntax=docker/dockerfile:1

FROM python

# Substitute real values with --build-arg options during build
ARG MASTOHOST=mastohost
ARG USERNAME=username
ARG CLIENTID=clientid
ARG CLIENTSECRET=clientsecret
ARG EVERDOAPIKEY=everdoapikey

SHELL ["bash", "-c"]

RUN apt-get update
RUN apt-get install -y vim

# vi mode everywhere
RUN cat <<EOBASHRC >> ~/.bashrc
export EDITOR=vi
set -o vi
bind -x '"\C-l": clear'
EOBASHRC

# Create required dirs from https://github.com/philcowans/fcli/blob/main/README.md#installation
RUN cat <<EODIRS | while read -r d; do mkdir -p ${d//\{*\}/~}; done
{$HOME}/.fcli/cache
{$HOME}/.fcli/outbox
{$HOME}/.fcli/processed/actionable
{$HOME}/.fcli/processed/actioned
{$HOME}/.fcli/processed/boostable
{$HOME}/.fcli/processed/boosted
{$HOME}/.fcli/processed/interesting
{$HOME}/.fcli/processed/not_interesting
{$HOME}/.fcli/processed/skipped
{$HOME}/.fcli/sent
{$HOME}/.fcli/staging
EODIRS

# Create config file
RUN mkdir -p ~/.config/fcli/ && cat <<EOCONFIG > ~/.config/fcli/config.ini
[Mastodon]
Server = $MASTOHOST
Username = $USERNAME
ClientID = $CLIENTID
ClientSecret = $CLIENTSECRET

[Everdo]
Key = $EVERDOAPIKEY
EOCONFIG

RUN cat <<EOREG > ~/mastoreg && chmod +x ~/mastoreg
#!/bin/sh
curl \
    --form 'client_name=fcli' \
    --form 'redirect_uris=urn:ietf:wg:oauth:2.0:oob' \
    --form 'scopes=read write' \
    --url "https://$MASTOHOST/api/v1/apps"
EOREG

# Clone fcli repo and perform install
RUN git clone https://github.com/philcowans/fcli ~/fcli \
    && cd $_ \
    && pip install -r requirements.txt

WORKDIR /root/fcli

CMD ["bash"]
