{ pkgs }:
let
  inherit (pkgs) lib;
in
pkgs.mkShell {
  nativeBuildInputs = with pkgs.python38Packages; [
    jobo_bot
    mypy
    requests
    beautifulsoup4
    python-telegram-bot
    selenium
    sqlalchemy
  ];
  shellHook = ''
    alias jobo_bot_="python jobo_bot"
  '';
}
