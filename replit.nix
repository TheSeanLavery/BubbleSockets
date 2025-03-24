{ pkgs }: {
  deps = [
    pkgs.python310
    pkgs.python310Packages.pip
    pkgs.python310Packages.websockets
    pkgs.python310Packages.msgpack
  ];
}
