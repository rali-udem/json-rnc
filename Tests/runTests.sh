#!/usr/bin/env bash
cd `dirname ${TM_FILEPATH:-.}`
testFiles=(*.jsonrnc) # create array of jsonrnc files

for file in ${testFiles[@]}
do
    name=`basename $file .jsonrnc`
    ../Src/ValidateJsonRnc.py -s --stats $name.jsonrnc $name.json | cmp $name.out
    if [ $? != 0 ]; then
        echo 'no match for: ' $file
    fi
done

../Src/SplitJson.py <TestSplitter.txt | cmp TestSplitter.out
if [ $? != 0 ]; then
    echo 'no match for: TestSplitter'
fi
echo "Test complete for `expr ${#testFiles[@]} + 1` files"

