
# PokeBase

A self-hosted Pokédex application, up to date through Gen 7.  
The database was created using CSVs from [Veekun](https://github.com/veekun/pokedex).

## How to Run

1. **Clone the repository**
````
git clone https://github.com/Leo-Expose/PokeBase.git
cd PokeBase
````

2. **Install Python requirements**

```bash
pip install -r requirements.txt
```

3. **Download data**

* Download `Database.zip` and `Sprites.zip` from the releases.
* Extract them.
* Move the `pokedex.sqlite` file to the `/data` folder.
* Move all sprite images to `/static/sprites/`.

4. **Run the app**

```bash
python app.py
```

5. **Open in browser**

Visit [http://localhost:5000](http://localhost:5000) to use the app.
