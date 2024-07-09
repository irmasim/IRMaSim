for scheduler in minimal brute; do
    rm -rf ${scheduler}/*
    if [ ${scheduler} == "brute" ]; then
        op="-nr 0"
    fi
    irmasim $op -o ${scheduler} options_${scheduler}.json
done
