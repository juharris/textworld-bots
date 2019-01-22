# textworld-bots
Bots to play [TextWorld](https://aka.ms/textworld).

# Setup

```bash
docker build -t tw .
```

* If you want to SSH into the container:
```bash
docker run --rm -it --detach -p 2022:22 -v ${PWD}:/root/workspace/textworld-bots --name tw tw bash
docker attach tw
# The prompt might not show, just press a key, e.g. the letter l.

nano ~/.ssh/authorized_keys
# Add you public key.

# Even though it was already done in the Dockerfile, to actually enable SSH, you might need to do.
service ssh restart 

# Ctrl P+Q to detach and keep the container running.

# To set up SSH:

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
