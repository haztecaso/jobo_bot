{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system}; in
      rec {
        packages = flake-utils.lib.flattenTree {
          jobo_bot = import ./default.nix { inherit pkgs; };
        };
        defaultPackage = packages.jobo_bot;
        devShell = pkgs.mkShell {
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
        };
      }
    );
}
