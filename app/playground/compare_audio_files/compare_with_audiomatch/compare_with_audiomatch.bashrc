#!/bin/bash

source ~/.bashrc
shopt -s extglob

F1=$1
F2=$2

# echo $F1, $F2;

AUDIOMATCH_RESULT=$(sudo docker run --rm -v "$(pwd)":/tmp fdooch/audiomatch "/tmp/*" {"/tmp/$F1","/tmp/$F2"})

N_F1=0
N_F2=0
N_SECTIONS=1
while IFS= read -r line ; do
	if [ "$line" = "/tmp/$F1" ]; then
		((N_F1=N_F1+1));
	fi
	if [ "$line" = "/tmp/$F2" ]; then
		((N_F2=N_F2+1));
	fi
	if [ "$line" = "---" ]; then
		((N_SECTIONS=N_SECTIONS+1));
	fi
done <<< "$AUDIOMATCH_RESULT"

# echo $AUDIOMATCH_RESULT;
# echo $N_F1, $N_F2, $N_SECTIONS;

# since a filename cannot occur twice in a section,
# if both filenames occur in one section one time each or
# if they both occur in two sections two times each, it means they co-occur
if ([ $N_F1 = 2 ] && [ $N_F2 = 2 ] $$ [ $N_SECTIONS = 2 ]) || ([ $N_F1 = 1 ] && [ $N_F2 = 1 ] && [ $N_SECTIONS = 1 ]); then
	echo "Files are similar";
else
	echo "Files are not similar";
fi

