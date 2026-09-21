int cellSize = 20;
float probabilityOfAliveAtStart = 15;

color alive = color(255);
color dead = color(0);

int cols, rows;
int[][] cells;
int[][] cellsBuffer;

void settings() {
  //feednplaySize(333, 555, P2D);
  feednplaySize(0, 0, 1080 * 9, 1920, P2D, true);
  //feednplayFullScreen(P2D);
  pixelDensity(1);
  noSmooth();
}

void setup() {
  frameRate(10);
  background(0);
  noStroke();
}

void draw() {
  if (frameCount < 100) {
    randomizeCells();
    return;
  }
  for (int x = 0; x < cols; x++) {
    for (int y = 0; y < rows; y++) {
      fill(cells[x][y] == 1 ? alive : dead);
      rect(x * cellSize, y * cellSize, cellSize, cellSize);
    }
  }
  iteration();
  if (frameCount % 10 * 60 * 2 == 0) {
    randomizeCells();
  }
}

void iteration() {
  for (int x = 0; x < cols; x++) {
    for (int y = 0; y < rows; y++) {
      cellsBuffer[x][y] = cells[x][y];
    }
  }
  for (int x = 0; x < cols; x++) {
    for (int y = 0; y < rows; y++) {
      int neighbours = 0;
      for (int xx = x - 1; xx <= x + 1; xx++) {
        for (int yy = y - 1; yy <= y + 1; yy++) {
          if (xx >= 0 && xx < cols && yy >= 0 && yy < rows && !(xx == x && yy == y)) {
            neighbours += cellsBuffer[xx][yy];
          }
        }
      }
      if (cellsBuffer[x][y] == 1) {
        cells[x][y] = (neighbours < 2 || neighbours > 3) ? 0 : 1;
      } else {
        cells[x][y] = (neighbours == 3) ? 1 : 0;
      }
    }
  }
}

void randomizeCells() {
  cols = width / cellSize;
  rows = height / cellSize;
  cells = new int[cols][rows];
  cellsBuffer = new int[cols][rows];
  for (int x = 0; x < cols; x++) {
    for (int y = 0; y < rows; y++) {
      cells[x][y] = random(100) < probabilityOfAliveAtStart ? 1 : 0;
    }
  }
}