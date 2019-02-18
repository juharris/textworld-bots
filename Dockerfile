FROM tavianator/textworld-codalab

RUN apt-get update

# For development:
RUN apt-get install --yes byobu htop nano zip

RUN apt-get install --yes openssh-server && (service ssh restart || service ssh start)
RUN mkdir ~/.ssh && touch ~/.ssh/authorized_keys

RUN pip3 install cherrypy expiringdict pytest

CMD ["bash"]
