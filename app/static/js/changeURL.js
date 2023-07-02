function changeURLByParam(tag, par) {
    tag = encodeURIComponent(tag);
    par = encodeURIComponent(par);
    let url = location.href;
    if (location.search == '' && !(/\?$/.test(url))) url += '?';
    let regexp = new RegExp(`(&${tag}=)([^&]*)`);

    if (regexp.test(url)) {
        if (par === '')
            url = url.replace(regexp, '');
        if (/\?$/.test(url)) url = url.slice(0, url.length - 1);
        else
            url = url.replace(regexp, '$1' + par);
    } else {
        url += `&${tag}=${par}`
    }

    history.pushState(null, null, url);
}

function changeURLByParamsList(listTag, data = []) {
    let url = location.href;
    listTag = encodeURIComponent(listTag);
    let regexp = new RegExp(`(&${listTag}=)([^&]*)`, 'g');

    if (location.search == '' && !(/\?$/.test(url))) url += '?';

    if (regexp.test(url)) {
        url = url.replace(regexp, '');
    }

    for (const value of data) {
        let valueEncoded = encodeURIComponent(value);

        url += `&${listTag}=${valueEncoded}`
    }

    if (/\?$/.test(url)) url = url.slice(0, url.length - 1);

    history.pushState(null, null, url);
}
