#!/usr/bin/env python
# -*- coding: utf-8 -*-
def winklerCompareP(str1, str2):
    """
    Source: http://stackoverflow.com/questions/2741872/python-performance-improvement-request-for-winkler
    Return approximate string comparator measure (between 0.0 and 1.0)
    Updated to include improvements.

    USAGE:
      score = winklerCompareP(str1, str2)

    ARGUMENTS:
      str1  The first string
      str2  The second string

    DESCRIPTION:
      As described in 'An Application of the Fellegi-Sunter Model of
      Record Linkage to the 1990 U.S. Decennial Census' by William E. Winkler
      and Yves Thibaudeau.

      Based on the 'jaro' string comparator, but modifies it according to whether
      the first few characters are the same or not.
    """

    # Quick check if the strings are the same
    jaro_winkler_marker_char = chr(1)
    if (str1 == str2):
        return 1.0

    len1 = len(str1)
    len2 = len(str2)
    halflen = max(len1,len2) / 2 - 1

    ass1  = ''  # Characters assigned in str1
    ass2  = '' # Characters assigned in str2
    workstr1 = str1
    workstr2 = str2
    # Number of common characters
    common1 = 0
    common2 = 0

    # Analyse the first string
    for i in range(len1):
        start = i - halflen if i > halflen else 0
        end = i+halflen+1 if i+halflen+1 < len2 else len2
        index = -1
        for j in xrange(start, end):
            if workstr2[j] == str1[i]:
                index = j
                break
        # Found common character.
        if (index > -1):
            common1 += 1
            #ass1 += str1[i]
            ass1 = ass1 + str1[i]
            workstr2 = workstr2[:index]+jaro_winkler_marker_char+workstr2[index+1:]
    # Analyse the second string.
    for i in range(len2):
        start = i - halflen if i > halflen else 0
        end = i+halflen+1 if i+halflen+1 < len2 else len2
        index = -1
        for j in xrange(start, end):
            if workstr1[j] == str2[i]:
                index = j
                break
        # Found common character
        if (index > -1):
            common2 += 1
            #ass2 += str2[i]
            ass2 = ass2 + str2[i]
            workstr1 = workstr1[:index]+jaro_winkler_marker_char+workstr1[index+1:]
    # This is just a fix #
    if (common1 != common2):
        common1 = float(common1+common2) / 2.0
    # Nothing in common.
    if (common1 == 0):
        return 0.0
    # Compute number of transpositions
    transposition = 0
    for i in range(len(ass1)):
        if (ass1[i] != ass2[i]):
            transposition += 1
    transposition = transposition / 2.0

    # Now compute how many characters are common at beginning
    minlen = min(len1, len2)
    for same in xrange(minlen):
        if str1[same] != str2[same]:
            break
    if (same > 4):
        same = 4

    common1 = float(common1)
    w = 1./3.*(common1 / float(len1) + common1 / float(len2) + (common1-transposition) / common1)

    wn = w + same*0.1 * (1.0 - w)
    return wn
