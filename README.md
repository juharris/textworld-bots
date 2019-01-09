# textworld-bots
Bots to play [TextWorld](https://aka.ms/textworld).

# Setup
Get the starting kit from [codalab][codalab].
Save `test_submission.py` in the repo root.

```bash
docker build -t tw .
docker run --rm -it -v ${PWD}:/root/tw --name tw tw python3 /root/tw/test_submission.py . /root/tw/all_games --in-docker
```

[codalab]: https://competitions.codalab.org/competitions/20865#participate-get_starting_kit
