import _ from 'lodash';
import { NamedPage } from '../misc/PageLoader';
import loadReactRedux from '../utils/loadReactRedux';

const page = new NamedPage('contest_balloon', () => {
    async function mountComponent() {
        const SockJs = await System.import('sockjs-client');
        const { default: BalloonPadApp } = await System.import('../components/balloonpad');
        const { default: BalloonPadReducer } = await System.import('../components/balloonpad/Reducer');
        const { React, render, Provider, store } = await loadReactRedux(BalloonPadReducer);

        const sock = new SockJs('/contest/balloon-conn');
        sock.onmessage = (message) => {
            const msg = JSON.parse(message.data);
            store.dispatch({
                type: 'BALLOON_MESSAGE_PUSH',
                payload: msg,
            });
        };


    }
});
