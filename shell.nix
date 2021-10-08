{ pkgs ? import <nixpkgs> {}}:
let
  inherit (pkgs) lib;
  jobo_bot = import ./default.nix { inherit pkgs lib; };
in
pkgs.mkShell {
  nativeBuildInputs = with pkgs.python38Packages; [
    jobo_bot
    requests
    beautifulsoup4
    tinydb
    python-telegram-bot
  ];
  shellHook = ''
    alias jobo_bot="python -m jobo_bot"
  '';
}
