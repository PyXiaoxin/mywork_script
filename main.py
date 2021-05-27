#!/usr/bin/python
# -*- coding: utf-8 -*-

from interface.connection import excel


def runStart(filename):
    filename_local = filename
    excel_obj = excel(filename_local)
    list_ex = excel_obj.excel_read()
    print(list_ex)


if __name__ == '__main__':
    filename = 'xiaoixn.xlsx'
    runStart(filename)
