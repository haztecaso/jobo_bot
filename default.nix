{ pkgs ? <nixpkgs> }:
pkgs.python38Packages.buildPythonPackage rec {
  pname = "jobo_bot";
  version = "1.1.0";

  src = ./.;

  propagatedBuildInputs = with pkgs.python38Packages; [
    requests
    beautifulsoup4
    python-telegram-bot
    selenium
    sqlalchemy
  ];

  # checkInputs = [ pytest ];
  # checkPhase = "pytest";

  meta = with pkgs.lib; {
    homepage = "https://github.com/haztecaso/jobo_bot";
    description = "Bot para recibir avisos de los eventos de jobo";
    license = licenses.gpl3;
  };
}
