{ pkgs ? import <nixpkgs> {}}:
let
  inherit (pkgs) lib;
  jobo_bot = import ./default.nix { inherit pkgs; };
in
pkgs.mkShell {
  nativeBuildInputs = with pkgs.python38Packages; [
    mypy
    jobo_bot
    requests
    beautifulsoup4
    python-telegram-bot
    selenium
    sqlalchemy
  ];
  shellHook = ''
    alias jobo_bot="python jobo_bot.py"
  '';
}
