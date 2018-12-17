FROM tavianator/textworld-codalab

RUN apt-get install --yes byobu htop nano

RUN apt-get install --yes openssh-server && (service ssh restart || service ssh start)
RUN mkdir ~/.ssh && touch ~/.ssh/authorized_keys

RUN pip3 install pytest

CMD ["bash"]
