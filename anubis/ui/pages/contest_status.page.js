/**
 * Created by Nitori on 2017/4/21.
 */
import { NamedPage } from '../misc/PageLoader';

const page = new NamedPage('contest_status', async () => {
    const SockJs = await System.import('sockjs-client');
    const sock = new SockJs(`/contest/${Context.tid}/notification-conn`);

    sock.onmessage = message => {
        const msg = JSON.parse(message.data);
        if (msg.type === 'rank_changed') {
            window.location.reload();
        }
    };
});

export default page;
