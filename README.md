[![Build Status](https://travis-ci.org/reticulatingspline/NFL.svg?branch=master)](https://travis-ci.org/reticulatingspline/NFL)

# Limnoria plugin for NFL Football things

## Introduction

This is a plugin to display various NFL football things like player stats, etc.

## Install

You will need a working Limnoria bot on Python 2.7 for this to work.

Go into your Limnoria plugin dir, usually ~/supybot/plugins and run:

```
git clone https://github.com/reticulatingspline/NFL
```

To install additional requirements, run:

```
pip install -r requirements.txt 
```

Next, load the plugin:

```
/msg bot load NFL
```

To use any player functions, you need a Bing API key.

Sign up for Bing's Web Results only at:
https://datamarket.azure.com/dataset/bing/searchweb

Then use the key that is displayed here:

https://datamarket.azure.com/account/keys

You will now need a Bing API key to use any player functions. This can be set via the:

```
/msg bot config.NFL.bingAPIkey longapikey

```

Now reload the bot:

```
/msg bot reload NFL
```

## Example Usage

```
<spline> @list NFL
<myybot> <lists NFL commands>
```

## About

All of my plugins are free and open source. When I first started out, one of the main reasons I was
able to learn was due to other code out there. If you find a bug or would like an improvement, feel
free to give me a message on IRC or fork and submit a pull request. Many hours do go into each plugin,
so, if you're feeling generous, I do accept donations via PayPal below.

I'm always looking for work, so if you are in need of a custom feature, plugin or something bigger, contact me via GitHub or IRC.

[![Donate via PayPal](https://www.paypalobjects.com/en_US/i/btn/btn_donate_SM.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=N2MKJ2CVZQE96&lc=US&currency_code=USD&bn=PP%2dDonationsBF%3abtn_donate_SM%2egif%3aNonHosted)
