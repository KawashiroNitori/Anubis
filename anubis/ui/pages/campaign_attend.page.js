/**
 * Created by Nitori on 2017/4/3.
 */
import { NamedPage } from '../misc/PageLoader';
import loadReactRedux from '../utils/loadReactRedux';


const page = new NamedPage(['campaign_attend'], () => {
    async function mountComponent() {
        $('.loader-container').show();

        const { default: AttendForm } = await System.import('../components/attendform');
        const { default: AttendFormReducer } = await System.import('../components/attendform/reducers');
        const { React, render, Provider, store } = await loadReactRedux(AttendFormReducer);

        render(
            <Provider store={store}>
                <AttendForm info={Context.teamInfo} />
            </Provider>,
            $('#attendForm').get(0),
        );

        $('.loader-container').hide();
    }

    mountComponent();
});

export default page;
