FROM continuumio/miniconda3 

RUN apt-get update --yes && \
    apt-get install htop --yes && \
    apt-get install vim --yes && \
    apt-get install gcc --yes && \
    apt-get install g++ --yes && \
    apt-get install libpq-dev --yes && \
    apt-get install python-dev --yes

RUN echo "alias ll='ls -alF'" >> ~/.bashrc && \
    echo "alias la='ls -A'" >> ~/.bashrc && \
    echo "alias l='ls -CF'" >> ~/.bashrc

COPY requirements.txt .
RUN pip install -r requirements.txt
