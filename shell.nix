{ pkgs ? import <nixpkgs> {}}:
let
  nixPackages = with pkgs.python38Packages; [
    requests
    beautifulsoup4
    tinydb
    python-telegram-bot
  ];
in
pkgs.stdenv.mkDerivation {
  name = "jobo-env";
  nativeBuildInputs = nixPackages;
  # shellHook = ''
  # '';
}
