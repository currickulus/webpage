# currickulus.xyz

Personal portfolio and project showcase site — live at [currickulus.xyz](https://currickulus.xyz)

## Overview

The landing page uses an image-mapped grid navigation system: a 7×9 invisible grid is overlaid on a full-viewport background image, and clicking specific cells routes to different pages. No nav bar, no buttons — the interface is embedded in the image itself.

## Pages

| Route | Description |
|---|---|
| `index.html` | Landing page with grid-mapped image navigation |
| `sierpinski.html` | WebGL Sierpinski triangle fractal renderer |
| `spinning_cube.html` | WebGL spinning cube with real-time 3D transforms |
| `polyfit.html` | Polynomial curve fitting visualization |
| `unit-circle.html` | Interactive unit circle reference |
| `mortar_simulator.html` | React ballistics / mortar trajectory simulator |
| `auth.html` | Authentication page |
| `terminal.html` | Browser-based terminal (authenticated) |
| `file-browser.html` | File browser (authenticated) |

## How the Navigation Works

The landing page loads a full-screen background image and overlays a CSS grid (`9 columns × 7 rows`) of transparent, clickable cells. Each cell covers a region of the image. Hovering reveals a subtle green highlight. Clicking a mapped cell navigates to the corresponding page — certain pages require authentication via localStorage token.

```
Grid cell (row, col) → destination
(0, 4) → sierpinski.html
(1, 4) → spinning_cube.html
(2, 4) → terminal.html       [auth required]
(3, 4) → auth.html
(4, 4) → file-browser.html   [auth required]
(5, 3) → polyfit.html
(5, 5) → unit-circle.html
(5, 6) → mortar_simulator.html
```

The grid recalculates on window resize to stay aligned with the image.

## Tech Stack

- Vanilla HTML / CSS / JavaScript
- WebGL + GLSL shaders (Sierpinski triangle, spinning cube)
- React (mortar simulator)
- CSS Grid for overlay layout
- localStorage-based auth token

## Local Development

No build step required. Clone the repo and open `index.html` directly in a browser, or serve locally:

```bash
git clone https://github.com/currickulus/webpage.git
cd webpage
python3 -m http.server 8080
# then open http://localhost:8080
```

## Author

Thomas Dewing — [LinkedIn](https://www.linkedin.com/in/thomas-dewing-7a24052b4) · [GitHub](https://github.com/currickulus)
