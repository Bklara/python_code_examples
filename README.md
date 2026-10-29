# python_code_examples
1. simple web app to internal purposes https://github.com/Bklara/python_code_examples/blob/master/web_app.py
![start](Screenshot%20from%202018-04-05%2018-43-25.png?raw=true "Title")
![click](Screenshot%20from%202018-04-05%2018-46-15.png?raw=true "Title")
2. and multiprocessing "request sender" https://github.com/Bklara/python_code_examples/blob/master/check_spell.py

3. simple baselines vs "smart" encoders for 15-step return prediction https://github.com/Bklara/python_code_examples/blob/master/financial_baselines.py
   (numpy-only toy version of the protocol from "Towards Financial World Modeling", arXiv:2610.09048:
   ridge on last 24 tokens, random untrained encoder, PCA, supervised and multi-head MLP; rank IC per regime,
   effective dimensionality, sector probe). Run: `python financial_baselines.py --seed 2`
