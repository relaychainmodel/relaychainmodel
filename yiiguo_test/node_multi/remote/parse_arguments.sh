#!/bin/bash

POSITIONAL_ARGS=()
GENERATE=0
BUILD=0
SAVE=0
SEND=0
VALUE=0

while [[ $# -gt 0 ]]; do
  case $1 in
    -g|--generate)
      VALUE=15
    -b|--build)
      VALUE=7
      shift # past argument
      ;;
    -s|--save)
      VALUE=3
      shift # past argument
      ;;
    -S|--send)
      VALUE=1
      shift # past argument
      ;;
    -*|--*)
      echo "Unknown option $1"
      exit 1
      ;;
    *)
      POSITIONAL_ARGS+=("$1") # save positional arg
      shift # past argument
      ;;
  esac
done

set -- "${POSITIONAL_ARGS[@]}" # restore positional parameters

echo "build: $BUILD"
echo "save: $SAVE"
echo "send: $SEND"