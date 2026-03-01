const board = document.getElementById("board");
board.style.display = "grid";
board.style.gridTemplateColumns = "repeat(8,50px)";

for(let i=0;i<64;i++){
  const d = document.createElement("div");
  d.style.width="50px";
  d.style.height="50px";
  d.style.background = (Math.floor(i/8)+i)%2==0?"#f0d9b5":"#b58863";
  board.appendChild(d);
}
