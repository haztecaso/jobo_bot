{ pkgs ? import <nixpkgs> {}}:
pkgs.mkShell {
  nativeBuildInputs = with pkgs.python38Packages; [
    mypy
    sqlalchemy
  ];
}
