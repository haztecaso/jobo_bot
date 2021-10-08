{ pkgs, lib }:
with pkgs.python38Packages;
buildPythonPackage rec {
  pname = "jobo_bot";
  version = "1.1.0";

  src = ./.;

  propagatedBuildInputs = [
    requests
    beautifulsoup4
    tinydb
    python-telegram-bot
  ];

  meta = with lib; {
    homepage = "https://github.com/haztecaso/jobo_bot";
    description = "Bot para recibir avisos de los eventos de jobo";
    license = licenses.gpl3;
  };
}

