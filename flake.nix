{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
      requirements = with pkgs.python38Packages; [
        requests
        beautifulsoup4
        python-telegram-bot
        selenium
        sqlalchemy
        pkgs.chromium
        pkgs.chromedriver
      ];
    in
      rec {
        packages = flake-utils.lib.flattenTree {
          jobo_bot = pkgs.python38Packages.buildPythonPackage rec {
            pname = "jobo_bot";
            version = "1.2.0";
          
            src = ./.;
          
            propagatedBuildInputs = requirements;
          
            meta = with pkgs.lib; {
              homepage = "https://github.com/haztecaso/jobo_bot";
              description = "Bot para recibir avisos de los eventos de jobo";
              license = licenses.gpl3;
            };
          };
        };
        defaultPackage = packages.jobo_bot;
        devShell = pkgs.mkShell {
          nativeBuildInputs = requirements ++ (with pkgs.python38Packages; [
            # packages.jobo_bot
            mypy
          ]);
          shellHook = ''
            alias jobo_bot_="python jobo_bot"
          '';
        };
      }
    );
}
