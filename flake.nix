{
  description = "Bot para recibir avisos de los eventos de jobo.";

  inputs.nixpkgs.url = "github:nixos/nixpkgs";

  outputs = { self, nixpkgs }:
  let
    supportedSystems = [ "aarch64-linux" "aarch64-darwin" "i686-linux" "x86_64-darwin" "x86_64-linux" ];
    forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);

    requirements = python38Packages: with python38Packages; [
        requests
        beautifulsoup4
        python-telegram-bot
        sqlalchemy
    ];

    jobo_bot = {lib, python38Packages}: python38Packages.buildPythonPackage rec {
      pname = "jobo_bot";
      version = "1.2.0";

      src = ./.;

      propagatedBuildInputs = requirements python38Packages;

      meta = {
        homepage = "https://github.com/haztecaso/jobo_bot";
        description = "Bot para recibir avisos de los eventos de jobo";
        license = lib.licenses.gpl3;
      };
    };
  in rec {
    packages = forAllSystems (system: {
      jobo_bot = nixpkgs.legacyPackages.${system}.callPackage jobo_bot { };
    });

    defaultPackage = forAllSystems (system: packages.${system}.jobo_bot);

    nixosModule = { config, lib, pkgs, ... }:
    let
      cfg = config.services.jobo_bot;
    in
    {
      options.services.jobo_bot = with lib;{
        enable = mkEnableOption "jobo_bot service";
        frequency = mkOption {
          type = types.int;
          default = 30;
          description = "frequency of cron job in minutes.";
        };
        prod = mkOption {
          type = types.bool;
          default = false;
          description = "enable production mode";
        };
        configFile = mkOption {
          type = types.path;
          description = "path of jobo_bot.json config file."; 
        };
      };
      config = lib.mkIf cfg.enable {
        environment.systemPackages = with pkgs; [ jobo_bot ];
        services.cron = {
          enable = true;
          systemCronJobs = let
            freq = lib.strings.floatToString cfg.frequency;
            conf = "--conf ${cfg.configFile}";
            prod = if cfg.prod then "--prod" else "";
          in [
            ''*/${freq} * * * *  root .  /etc/profile; ${pkgs.jobo_bot}/bin/jobo_bot ${conf} ${prod}''
          ];
        };
      };
    };

    devShell = forAllSystems (system: nixpkgs.legacyPackages.${system}.mkShell {
      nativeBuildInputs = with nixpkgs.legacyPackages.${system};
        requirements python38Packages ++ [ jq fx ];
      shellHook = ''
        alias jobo_bot_="python jobo_bot"
      '';
    });

    overlay = final: prev: {
      jobo_bot = final.callPackage jobo_bot {};
    };
  };
}
