# textworld-bots
Bots to play [TextWorld](https://aka.ms/textworld).

# Setup

```bash
docker build -t tw .

# To set up SSH:
docker run --rm -it --detach -p 2022:22 -v ${PWD}:/root/tw --name tw tw bash
```

# Running games
Copy games into all_games/train.

Then run: 
```bash
docker run --rm -it -v ${PWD}:/root/tw --name tw tw python3 /root/tw/test_submission.py . /root/tw/all_games --in-docker
```

# Testing
Run:
```bash
docker run --rm -it -v ${PWD}:/root/tw --name tw tw python3 -m unittest discover /root/tw
```

[codalab]: https://competitions.codalab.org/competitions/20865#participate-get_starting_kit
